"""
pdf_extractor.py — PDF download + text extraction tool for CrewAI.
Exact port from multi-agent-research-system-2.
"""

import io
import logging
import os
import re
from typing import Type

import requests
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

HARD_TEXT_LIMIT = 3_000
MAX_PAGES       = 15
MAX_DOWNLOAD_MB = 10


class _PDFInput(BaseModel):
    url: str = Field(..., description="Direct URL to a PDF file (e.g. arXiv abstract or direct link)")


class PDFExtractorTool(BaseTool):
    name: str = "PDF Text Extractor"
    description: str = (
        "Download a PDF from a URL and extract readable plain text. "
        "Returns at most 3 000 characters of the most relevant content. "
        "Works best with arXiv, IEEE, and ACL papers."
    )
    args_schema: Type[BaseModel] = _PDFInput

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _run(self, url: str) -> str:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return "Error: PyMuPDF (fitz) is not installed. Run: pip install PyMuPDF"

        if "arxiv.org/abs/" in url:
            url = url.replace("/abs/", "/pdf/") + ".pdf"

        logger.info("Downloading PDF: %s", url)

        resp = requests.get(
            url,
            headers={"User-Agent": "ResearchCrew/1.0 (academic crawler)"},
            timeout=30,
            stream=True,
        )
        resp.raise_for_status()

        content = b""
        max_bytes = MAX_DOWNLOAD_MB * 1024 * 1024
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_bytes:
                logger.warning("PDF exceeds %d MB cap – truncating download.", MAX_DOWNLOAD_MB)
                break

        doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
        pages_read = min(len(doc), MAX_PAGES)

        text_parts = []
        for page_num in range(pages_read):
            page = doc[page_num]
            text_parts.append(page.get_text("text"))

        doc.close()

        full_text = "\n".join(text_parts)
        full_text = _clean_pdf_text(full_text)

        truncated = full_text[:HARD_TEXT_LIMIT]
        logger.info("PDF extracted: %d chars (from %d pages).", len(truncated), pages_read)
        return truncated


def _clean_pdf_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\x0c", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)
