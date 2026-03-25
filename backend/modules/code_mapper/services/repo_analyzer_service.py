"""
Repository Analyzer Service — Clone, parse, and extract structure from GitHub repos.

Pipeline:
  1. Shallow-clone the repo into a temp directory
  2. Walk the file tree, identify key files (models, training, config, README)
  3. Parse Python files with ``ast`` to extract classes, functions, docstrings
  4. Summarise per-module via LLM
  5. Return a ``RepoStructure`` used by the paper-writing pipeline
"""

from __future__ import annotations

import ast
import asyncio
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from modules.code_mapper.models.code_mapper_models import RepoFileInfo, RepoStructure
from modules.code_mapper.services import llm_client

logger = logging.getLogger(__name__)

_CLONE_DIR = Path(tempfile.gettempdir()) / "code_mapper_repos"
_CLONE_DIR.mkdir(parents=True, exist_ok=True)

_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", ".tox", ".mypy_cache", ".pytest_cache", "dist",
    "build", "egg-info", ".eggs", "wandb", "runs",
}

_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java",
    ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".scala",
}

_MAX_FILES_TO_ANALYZE = 80
_MAX_FILE_SIZE = 100_000  # bytes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_repo(github_url: str, job_id: str) -> RepoStructure:
    """Clone and fully analyze a GitHub repository."""

    repo_path = await _clone_repo(github_url, job_id)
    file_tree = _walk_tree(repo_path)
    key_files = _identify_key_files(repo_path, file_tree)
    readme = _read_readme(repo_path)
    classes, functions = _parse_python_ast(repo_path, file_tree)
    languages = _detect_languages(file_tree)
    config_files = [f for f in file_tree if _is_config(f)]
    training_scripts = [f for f in file_tree if _is_training_script(f)]

    summaries = await _summarise_key_files(key_files, repo_path)
    for kf, summary in zip(key_files, summaries):
        kf.summary = summary

    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")

    return RepoStructure(
        name=repo_name,
        description=readme[:500] if readme else "",
        languages=languages,
        total_files=len(file_tree),
        file_tree=file_tree[:200],
        key_files=key_files,
        readme_content=readme[:10_000],
        classes=classes[:50],
        functions=functions[:80],
        config_files=config_files[:20],
        training_scripts=training_scripts[:10],
    )


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

async def _clone_repo(url: str, job_id: str) -> Path:
    dest = _CLONE_DIR / job_id
    if dest.exists():
        import shutil
        shutil.rmtree(dest, ignore_errors=True)

    clean_url = _sanitize_url(url)
    rc, stderr = await asyncio.to_thread(_run_git_clone, clean_url, dest, 120)
    if rc != 0:
        raise RuntimeError(f"git clone failed: {stderr[:500]}")

    return dest


def _run_git_clone(clean_url: str, dest: Path, timeout_seconds: int) -> tuple[int, str]:
    """Run `git clone` in a blocking way, suitable for Windows."""
    completed = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            clean_url,
            str(dest),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    return completed.returncode, completed.stderr or ""


def _sanitize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("https://", "http://")):
        url = "https://github.com/" + url.lstrip("/")
    if not url.endswith(".git"):
        url = url.rstrip("/") + ".git"
    return url


# ---------------------------------------------------------------------------
# File tree walking
# ---------------------------------------------------------------------------

def _walk_tree(root: Path) -> list[str]:
    result: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        for fname in filenames:
            rel = str(rel_dir / fname).replace("\\", "/")
            if rel.startswith("./"):
                rel = rel[2:]
            result.append(rel)
    return sorted(result)


def _identify_key_files(root: Path, tree: list[str]) -> list[RepoFileInfo]:
    """Rank files by importance and return top candidates for analysis."""

    scored: list[tuple[float, str]] = []
    for rel in tree:
        ext = Path(rel).suffix.lower()
        if ext not in _CODE_EXTENSIONS and rel.lower() not in ("readme.md", "readme.rst", "readme.txt"):
            continue
        fpath = root / rel
        if not fpath.is_file():
            continue
        size = fpath.stat().st_size
        if size > _MAX_FILE_SIZE or size == 0:
            continue

        score = _importance_score(rel)
        scored.append((score, rel))

    scored.sort(key=lambda x: -x[0])
    top = scored[:_MAX_FILES_TO_ANALYZE]

    result: list[RepoFileInfo] = []
    for score, rel in top:
        fpath = root / rel
        lang = Path(rel).suffix.lstrip(".")
        result.append(
            RepoFileInfo(
                path=rel,
                language=lang,
                size_bytes=fpath.stat().st_size,
            )
        )
    return result


def _importance_score(rel: str) -> float:
    name = rel.rsplit("/", 1)[-1].lower()
    score = 1.0

    high_value = [
        "model", "train", "main", "config", "dataset", "data",
        "network", "loss", "evaluate", "inference", "agent",
        "architecture", "backbone", "encoder", "decoder",
    ]
    for kw in high_value:
        if kw in name:
            score += 5.0

    if name in ("readme.md", "setup.py", "pyproject.toml"):
        score += 3.0

    depth = rel.count("/")
    score -= depth * 0.3

    if "test" in rel.lower() or "example" in rel.lower():
        score -= 2.0

    return score


# ---------------------------------------------------------------------------
# AST parsing
# ---------------------------------------------------------------------------

def _parse_python_ast(
    root: Path, tree: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []

    py_files = [f for f in tree if f.endswith(".py")]
    for rel in py_files[:60]:
        fpath = root / rel
        if not fpath.is_file() or fpath.stat().st_size > _MAX_FILE_SIZE:
            continue
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
            parsed = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(parsed):
            if isinstance(node, ast.ClassDef):
                bases = [_name(b) for b in node.bases]
                classes.append({
                    "name": node.name,
                    "file": rel,
                    "bases": bases,
                    "docstring": ast.get_docstring(node) or "",
                    "methods": [
                        m.name for m in node.body
                        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ],
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if isinstance(node, ast.FunctionDef) and _is_top_level(node, parsed):
                    args = [a.arg for a in node.args.args if a.arg != "self"]
                    functions.append({
                        "name": node.name,
                        "file": rel,
                        "args": args[:10],
                        "docstring": ast.get_docstring(node) or "",
                    })

    return classes, functions


def _name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    return "?"


def _is_top_level(node: ast.FunctionDef, module: ast.Module) -> bool:
    return node in module.body


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def _detect_languages(tree: list[str]) -> list[str]:
    ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".java": "Java", ".cpp": "C++", ".c": "C", ".go": "Go",
        ".rs": "Rust", ".rb": "Ruby", ".scala": "Scala",
        ".jsx": "React", ".tsx": "React/TS",
    }
    counts: dict[str, int] = {}
    for f in tree:
        ext = Path(f).suffix.lower()
        lang = ext_map.get(ext)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return sorted(counts, key=lambda l: -counts[l])


# ---------------------------------------------------------------------------
# Config / training detection
# ---------------------------------------------------------------------------

def _is_config(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1].lower()
    return any(
        name.endswith(ext) for ext in (".yaml", ".yml", ".json", ".toml", ".cfg", ".ini")
    ) or name in ("config.py", "settings.py", "hyperparams.py")


def _is_training_script(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1].lower()
    return any(kw in name for kw in ("train", "run", "main", "experiment", "finetune"))


def _read_readme(root: Path) -> str:
    for name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="ignore")[:10_000]
    return ""


# ---------------------------------------------------------------------------
# LLM summarisation of key files
# ---------------------------------------------------------------------------

async def _summarise_key_files(
    files: list[RepoFileInfo], root: Path
) -> list[str]:
    """Produce a one-paragraph summary for each key file."""

    summaries: list[str] = []
    batch_files: list[tuple[RepoFileInfo, str]] = []

    for kf in files:
        fpath = root / kf.path
        if not fpath.is_file():
            summaries.append("")
            continue
        content = fpath.read_text(encoding="utf-8", errors="ignore")[:4000]
        batch_files.append((kf, content))

    if not batch_files:
        return summaries

    combined = "\n\n".join(
        f"### {kf.path}\n```\n{content}\n```"
        for kf, content in batch_files[:20]
    )

    system = (
        "You are a code analyst. For each file below, write a single concise sentence "
        "describing what it does. Return a JSON array of strings in the same order."
    )

    try:
        result = await llm_client.chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": combined}],
            max_tokens=2000,
            temperature=0.2,
        )
        raw_list = result.get("summaries", result.get("results", []))
        if isinstance(raw_list, list):
            for i, (kf, _) in enumerate(batch_files):
                s = raw_list[i] if i < len(raw_list) else ""
                summaries.append(str(s))
        else:
            summaries.extend([""] * len(batch_files))
    except Exception:
        logger.warning("LLM file summarisation failed, using empty summaries")
        summaries.extend([""] * len(batch_files))

    return summaries
