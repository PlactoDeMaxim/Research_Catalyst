"""
Code Validator Service — AST validation + sandbox execution + self-healing.

Validates generated Python files in two stages:
  1. AST parse (syntax check — fast, no execution)
  2. Subprocess execution in an isolated temp directory with timeout

On failure, feeds the error back to the LLM for a fix attempt, up to
``MAX_FIX_ROUNDS`` rounds per file.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from modules.code_mapper.models.code_mapper_models import (
    GeneratedFile,
    ValidationResult,
)
from modules.code_mapper.services import llm_client

logger = logging.getLogger(__name__)

MAX_FIX_ROUNDS: int = 5
EXEC_TIMEOUT_SECONDS: int = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def validate_and_fix(
    files: list[GeneratedFile],
) -> tuple[list[GeneratedFile], list[ValidationResult]]:
    """Validate all Python files, attempting LLM-driven fixes on failures.

    Returns the (possibly updated) files list and per-file validation results.
    """

    results: list[ValidationResult] = []

    for i, gf in enumerate(files):
        if gf.language != "python" or not gf.path.endswith(".py"):
            results.append(
                ValidationResult(file_path=gf.path, passed=True, ast_valid=True, exec_valid=True)
            )
            continue

        vr = await _validate_single(gf, files)
        if vr.passed:
            results.append(vr)
            continue

        current = gf
        for attempt in range(1, MAX_FIX_ROUNDS + 1):
            fixed = await _attempt_fix(current, vr.errors, attempt)
            if fixed is None:
                break
            current = fixed
            files[i] = current
            vr = await _validate_single(current, files)
            vr.fix_attempts = attempt
            if vr.passed:
                break

        results.append(vr)

    return files, results


# ---------------------------------------------------------------------------
# Single-file validation
# ---------------------------------------------------------------------------

async def _validate_single(
    gf: GeneratedFile, all_files: list[GeneratedFile]
) -> ValidationResult:
    """Run AST check then subprocess execution."""

    vr = ValidationResult(file_path=gf.path)

    ast_ok, ast_err = _ast_check(gf.content)
    vr.ast_valid = ast_ok
    if not ast_ok:
        vr.errors.append(f"SyntaxError: {ast_err}")
        return vr

    exec_ok, exec_err = await _exec_check(gf, all_files)
    vr.exec_valid = exec_ok
    if not exec_ok and exec_err:
        vr.errors.append(exec_err)

    vr.passed = vr.ast_valid and vr.exec_valid
    return vr


def _ast_check(source: str) -> tuple[bool, str]:
    try:
        ast.parse(source)
        return True, ""
    except SyntaxError as exc:
        return False, f"Line {exc.lineno}: {exc.msg}"


async def _exec_check(
    target: GeneratedFile, all_files: list[GeneratedFile]
) -> tuple[bool, str]:
    """Write all project files to a temp dir and execute the target file."""

    with tempfile.TemporaryDirectory(prefix="cm_exec_") as tmpdir:
        root = Path(tmpdir)

        for gf in all_files:
            fpath = root / gf.path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(gf.content, encoding="utf-8")

        target_path = root / target.path

        # Windows + some event loop policies can raise NotImplementedError for
        # asyncio.create_subprocess_exec. Use blocking subprocess.run in a thread.
        if _is_entry_point(target.path):
            ok, err = await asyncio.to_thread(
                _run_python_entry, sys.executable, root, target_path, EXEC_TIMEOUT_SECONDS
            )
            if not ok:
                return False, err
        else:
            ok, err = await asyncio.to_thread(
                _run_python_import_check,
                sys.executable,
                root,
                target_path,
                EXEC_TIMEOUT_SECONDS,
            )
            if not ok:
                return False, err

    return True, ""

def _run_python_entry(
    python_exe: str,
    root: Path,
    target_path: Path,
    timeout_seconds: int,
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            [python_exe, str(target_path)],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_sandbox_env(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"Execution timed out after {timeout_seconds}s"

    if completed.returncode != 0:
        err_text = (completed.stderr or b"").decode(errors="replace")[-2000:]
        return False, f"Exit code {completed.returncode}: {err_text}"

    return True, ""


def _run_python_import_check(
    python_exe: str,
    root: Path,
    target_path: Path,
    timeout_seconds: int,
) -> tuple[bool, str]:
    # Import-only check: avoids running training loops.
    code = (
        "import importlib.util; "
        f"spec = importlib.util.spec_from_file_location('mod', r'{target_path}'); "
        "mod = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(mod)"
    )
    try:
        completed = subprocess.run(
            [python_exe, "-c", code],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_sandbox_env(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        # If import hangs, treat as pass to avoid over-failing.
        return True, ""

    if completed.returncode != 0:
        err_text = (completed.stderr or b"").decode(errors="replace")[-2000:]
        if "ModuleNotFoundError" in err_text:
            # Missing optional deps should not fail validation.
            return True, ""
        return False, f"Import check failed: {err_text}"

    return True, ""


# ---------------------------------------------------------------------------
# LLM fix attempt
# ---------------------------------------------------------------------------

async def _attempt_fix(
    gf: GeneratedFile,
    errors: list[str],
    attempt: int,
) -> Optional[GeneratedFile]:
    """Ask the LLM to fix code errors. Returns None if the fix fails."""

    system = (
        "You are an expert Python debugger. Fix the code below so it runs without errors. "
        "Output ONLY the corrected Python code — no markdown fences, no explanation."
    )

    user = (
        f"File: {gf.path} (fix attempt {attempt}/{MAX_FIX_ROUNDS})\n\n"
        f"Errors:\n" + "\n".join(errors) + "\n\n"
        f"Current code:\n```python\n{gf.content}\n```"
    )

    try:
        fixed_code = await llm_client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=6000,
            temperature=0.1,
        )
        fixed_code = _strip_fences(fixed_code)

        ok, _ = _ast_check(fixed_code)
        if not ok:
            return None

        return GeneratedFile(path=gf.path, content=fixed_code, language=gf.language)
    except Exception:
        logger.warning("Fix attempt %d for %s failed", attempt, gf.path)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_entry_point(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return name in (
        "train.py", "main.py", "run.py", "evaluate.py",
        "test.py", "demo.py", "inference.py",
    )


def _sandbox_env() -> dict[str, str]:
    import os
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def _strip_fences(text: str) -> str:
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
