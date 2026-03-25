"""
Packager Service — Assemble generated code into a downloadable ZIP.

Writes all generated files into a temp directory, then creates a ZIP
archive with proper project structure.
"""

from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path

from modules.code_mapper.models.code_mapper_models import CodeBlueprint, GeneratedFile

logger = logging.getLogger(__name__)

_WORK_DIR = Path(tempfile.gettempdir()) / "code_mapper_packages"
_WORK_DIR.mkdir(parents=True, exist_ok=True)


def package_project(
    blueprint: CodeBlueprint,
    files: list[GeneratedFile],
    job_id: str,
) -> Path:
    """Write all files to a temp directory and create a ZIP archive.

    Returns the path to the created ZIP file.
    """

    project_dir = _WORK_DIR / job_id / blueprint.project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    for gf in files:
        file_path = project_dir / gf.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(gf.content, encoding="utf-8")

    zip_path = _WORK_DIR / job_id / f"{blueprint.project_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(project_dir.rglob("*")):
            if file_path.is_file():
                arcname = str(file_path.relative_to(project_dir.parent))
                zf.write(file_path, arcname)

    logger.info("Packaged %d files into %s", len(files), zip_path)
    return zip_path


def get_package_path(job_id: str) -> Path | None:
    """Return the ZIP path for a given job, or None if not found."""
    job_dir = _WORK_DIR / job_id
    if not job_dir.exists():
        return None
    zips = list(job_dir.glob("*.zip"))
    return zips[0] if zips else None
