from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
import traceback
import uuid
from pathlib import Path

from modules.paper_editor.models.paper_editor_models import JobStatusResponse
from modules.paper_editor.services import job_store
from modules.paper_editor.services.template_service import BASE_WORK_DIR

LATEX_COMPILE_MODE = os.getenv("PAPER_EDITOR_LATEX_MODE", "docker").strip().lower()
LATEX_IMAGE = os.getenv("PAPER_EDITOR_LATEX_IMAGE", "ghcr.io/xu-cheng/texlive-full:latest").strip()
LATEX_TIMEOUT_SECONDS = int(os.getenv("PAPER_EDITOR_LATEX_TIMEOUT_SECONDS", "240"))
LATEX_CPUS = os.getenv("PAPER_EDITOR_LATEX_CPUS", "1.5")
LATEX_MEMORY = os.getenv("PAPER_EDITOR_LATEX_MEMORY", "2g")
LATEX_PIDS_LIMIT = os.getenv("PAPER_EDITOR_LATEX_PIDS_LIMIT", "256")
COMPILE_JOB_ROOT = BASE_WORK_DIR / "_compile_jobs"
COMPILE_JOB_ROOT.mkdir(parents=True, exist_ok=True)


def _fix_unescaped_chars(text: str) -> str:
    # conservative content-only escaping pass
    text = text.replace(" %", r" \%")
    text = text.replace(" _", r" \_")
    text = text.replace(" &", r" \&")
    text = text.replace(" #", r" \#")
    return text


def _run_command(work_dir: Path, command: list[str], timeout_seconds: int) -> tuple[bool, str]:
    try:
        start = time.time()
        proc = subprocess.run(
            command,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        duration_ms = int((time.time() - start) * 1000)
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return proc.returncode == 0, f"[exit={proc.returncode} duration_ms={duration_ms}]\n{combined}"
    except subprocess.TimeoutExpired as exc:
        return False, f"timeout: {' '.join(command)}: {exc}"
    except FileNotFoundError as exc:
        return False, f"missing-executable: {' '.join(command)}: {exc}"


def _run_latexmk_local(work_dir: Path, tex_file: Path) -> tuple[bool, str]:
    latexmk_command = [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-g",
        tex_file.name,
    ]
    ok, log = _run_command(work_dir, latexmk_command, timeout_seconds=LATEX_TIMEOUT_SECONDS)
    return ok, f"[engine=latexmk-local]\n{log}"


def _run_pdflatex_local(work_dir: Path, tex_file: Path) -> tuple[bool, str]:
    chunks: list[str] = []
    for pass_index in range(1, 3):
        pdflatex_command = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            tex_file.name,
        ]
        ok, log = _run_command(work_dir, pdflatex_command, timeout_seconds=LATEX_TIMEOUT_SECONDS)
        chunks.append(f"[engine=pdflatex-local pass={pass_index}]\n{log}")
        if not ok:
            return False, "\n".join(chunks)
    return True, "\n".join(chunks)


def _latexmk_runtime_broken(log: str) -> bool:
    normalized = log.lower()
    return (
        "script engine not found" in normalized
        or "fix-script-engine-not-found" in normalized
        or "latexmk: major issue" in normalized
        or "missing-executable: latexmk" in normalized
    )


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        probe = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return probe.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _docker_image_present(image: str) -> bool:
    try:
        probe = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return probe.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def get_compile_preflight(_template_id: str) -> dict[str, object]:
    mode = LATEX_COMPILE_MODE if LATEX_COMPILE_MODE in {"docker", "local", "auto"} else "docker"
    docker_ready = _docker_available()
    image_ready = _docker_image_present(LATEX_IMAGE) if docker_ready else False
    warnings: list[str] = []
    if mode in {"docker", "auto"} and not docker_ready:
        warnings.append("Docker is not available. Start Docker Desktop or switch PAPER_EDITOR_LATEX_MODE=local.")
    if mode in {"docker", "auto"} and docker_ready and not image_ready:
        warnings.append(f"Docker image missing: {LATEX_IMAGE}. Run: docker pull {LATEX_IMAGE}")
    return {
        "template_id": _template_id,
        "mode": mode,
        "docker_ready": docker_ready,
        "image_ready": image_ready,
        "warnings": warnings,
    }


def _run_latexmk_container(work_dir: Path, tex_file: Path) -> tuple[bool, str]:
    host_dir = str(work_dir.resolve())
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cpus",
        LATEX_CPUS,
        "--memory",
        LATEX_MEMORY,
        "--pids-limit",
        LATEX_PIDS_LIMIT,
        "-v",
        f"{host_dir}:/work",
        "-w",
        "/work",
        LATEX_IMAGE,
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-g",
        tex_file.name,
    ]
    ok, log = _run_command(work_dir, command, timeout_seconds=LATEX_TIMEOUT_SECONDS + 180)
    return ok, f"[engine=latexmk-docker image={LATEX_IMAGE}]\n{log}"


def _compile_with_selected_engine(work_dir: Path, source_path: Path) -> tuple[bool, str, bool]:
    """
    Returns (ok, log, engine_unavailable).
    engine_unavailable is true when required runtime is missing/offline.
    """
    mode = LATEX_COMPILE_MODE
    if mode not in {"docker", "local", "auto"}:
        mode = "docker"

    if mode in {"docker", "auto"}:
        if _docker_available():
            if not _docker_image_present(LATEX_IMAGE):
                return (
                    False,
                    f"[engine=docker] Missing image {LATEX_IMAGE}. Run: docker pull {LATEX_IMAGE}",
                    True,
                )
            ok, log = _run_latexmk_container(work_dir, source_path)
            return ok, log, False
        if mode == "docker":
            return False, "[engine=docker] Docker is unavailable. Start Docker Desktop or set PAPER_EDITOR_LATEX_MODE=local.", True

    # local path for explicit local mode or auto fallback
    ok, latexmk_log = _run_latexmk_local(work_dir, source_path)
    combined_log = latexmk_log
    engine_unavailable = False
    if not ok and _latexmk_runtime_broken(latexmk_log):
        fallback_ok, fallback_log = _run_pdflatex_local(work_dir, source_path)
        combined_log = f"{latexmk_log}\n\n[fallback]\n{fallback_log}"
        ok = fallback_ok
        if "missing-executable: pdflatex" in fallback_log.lower():
            engine_unavailable = True
    elif not ok and "missing-executable: latexmk" in latexmk_log.lower():
        fallback_ok, fallback_log = _run_pdflatex_local(work_dir, source_path)
        combined_log = f"{latexmk_log}\n\n[fallback]\n{fallback_log}"
        ok = fallback_ok
        if "missing-executable: pdflatex" in fallback_log.lower():
            engine_unavailable = True
    return ok, combined_log, engine_unavailable


def _prepare_job_workspace(job_id: str, template_id: str, tex_path: Path) -> tuple[Path, Path]:
    template_work_dir = BASE_WORK_DIR / template_id
    if not template_work_dir.exists():
        raise RuntimeError(f"Template workspace missing: {template_work_dir}")

    job_dir = COMPILE_JOB_ROOT / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

    # Deterministic compile: copy template workspace into an isolated, clean per-job sandbox.
    shutil.copytree(template_work_dir, job_dir)

    injected_text = tex_path.read_text(encoding="utf-8", errors="ignore")
    try:
        rel_tex = tex_path.resolve().relative_to(template_work_dir.resolve())
    except ValueError:
        rel_tex = Path(tex_path.name)
    target_dir = (job_dir / rel_tex.parent).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    source_path = target_dir / "compiled_input.tex"
    source_path.write_text(injected_text, encoding="utf-8")

    for ext in (".aux", ".bbl", ".blg", ".fdb_latexmk", ".fls", ".log", ".out", ".pdf"):
        stale = job_dir / f"compiled_input{ext}"
        if stale.exists():
            stale.unlink(missing_ok=True)
    return job_dir, source_path


def _extract_missing_class_name(log_text: str) -> str | None:
    match = re.search(r"File `([^`]+\.cls)' not found", log_text)
    if match:
        return match.group(1)
    return None


def _execute_compile_job(job: JobStatusResponse, template_id: str, tex_path: Path, max_retries: int) -> None:
    job.status = "running"
    if LATEX_COMPILE_MODE == "docker":
        job.message = "Compiling injected template in isolated container"
    else:
        job.message = "Compiling injected template"
    job_store.save_job(job)

    logs: list[str] = []
    source_path: Path | None = None
    try:
        logs.append("[phase] preparing isolated compile workspace")
        job.message = "Preparing isolated compile workspace"
        job_store.save_job(job)
        job_dir, source_path = _prepare_job_workspace(job.job_id, template_id, tex_path)

        attempts = max(1, max_retries + 1)
        success = False
        artifact: Path | None = None
        engine_unavailable = False
        missing_cls_name: str | None = None

        for attempt in range(1, attempts + 1):
            logs.append(f"[phase] compile attempt {attempt}/{attempts}")
            job.message = f"Compiling PDF (attempt {attempt}/{attempts})"
            job_store.save_job(job)
            ok, compile_log, engine_missing = _compile_with_selected_engine(job_dir, source_path)
            if engine_missing:
                engine_unavailable = True
            if missing_cls_name is None:
                missing_cls_name = _extract_missing_class_name(compile_log)

            logs.append(f"[attempt {attempt}] {compile_log[-4000:]}")
            if ok:
                job.message = "Finalizing compiled artifact"
                job_store.save_job(job)
                pdf_candidate = job_dir / "compiled_input.pdf"
                if pdf_candidate.exists():
                    artifact = pdf_candidate
                else:
                    artifact = source_path
                success = True
                break

            current = source_path.read_text(encoding="utf-8", errors="ignore")
            fixed = _fix_unescaped_chars(current)
            source_path.write_text(fixed, encoding="utf-8")

        job.logs = logs
        if success:
            job.status = "succeeded"
            job.message = "Compilation succeeded."
            job.artifact_path = str(artifact) if artifact else None
        else:
            last_log = logs[-1] if logs else ""
            if engine_unavailable or "missing-executable: latexmk" in last_log.lower():
                job.message = (
                    "Compilation failed: container engine unavailable or no usable local LaTeX engine found."
                )
            elif missing_cls_name:
                job.message = (
                    f"Compilation failed: missing class file '{missing_cls_name}'. "
                    "If this is a custom template class, include the .cls in the uploaded ZIP near the main .tex."
                )
            else:
                condensed = last_log[-300:].replace("\n", " ").strip()
                job.message = f"Compilation failed after retries. {condensed}" if condensed else "Compilation failed after retries."
            job.status = "failed"
            job.artifact_path = str(source_path) if source_path else None
    except Exception as exc:  # defensive: never leave job in running state
        logs.append(f"[worker-exception] {type(exc).__name__}: {exc}\n{traceback.format_exc()[-3500:]}")
        job.logs = logs
        job.status = "failed"
        job.message = f"Compilation worker crashed: {type(exc).__name__}"
        job.artifact_path = str(source_path) if source_path and source_path.exists() else None
    finally:
        job_store.save_job(job)
    return None


def run_compile_job(_template_id: str, tex_path: Path, max_retries: int) -> JobStatusResponse:
    """Run compile synchronously (kept for internal/testing usage)."""
    job_id = str(uuid.uuid4())
    job = job_store.create_job(job_id)
    _execute_compile_job(job, _template_id, tex_path, max_retries)
    return job


def enqueue_compile_job(_template_id: str, tex_path: Path, max_retries: int) -> JobStatusResponse:
    """Queue compile in a background thread and return immediately."""
    job_id = str(uuid.uuid4())
    job = job_store.create_job(job_id)
    job.message = "Queued for compilation"
    job_store.save_job(job)

    worker = threading.Thread(
        target=_execute_compile_job,
        args=(job, _template_id, tex_path, max_retries),
        name=f"paper-editor-compile-{job_id[:8]}",
        daemon=True,
    )
    worker.start()
    return job
