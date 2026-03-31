"""
PDF Summarizer Service

Extracts text from uploaded PDFs and generates structured summaries
using Ollama Cloud API (same provider as code_mapper module).

Produces output in the same shape as parsed_papers.json entries:
  - title, authors, category, executive_summary, detailed_breakdown, original_abstract
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import time
from typing import Any

import httpx
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ollama Cloud Configuration (reuses code_mapper env vars)
# ---------------------------------------------------------------------------

def _ollama_config() -> dict[str, Any]:
    return {
        "api_key": os.getenv("OLLAMA_API_KEY", "").strip(),
        "base_url": os.getenv("OLLAMA_BASE_URL", "https://ollama.com").strip(),
        "model": os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud").strip(),
        "timeout": int(os.getenv("LLM_TIMEOUT", "300")),
    }


# ---------------------------------------------------------------------------
# PDF Text Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file's bytes."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _truncate_for_context(text: str, max_chars: int = 12000) -> str:
    """Truncate text to fit within LLM context limits.
    
    Tries to keep the beginning (title, abstract, intro) and some of
    the conclusion/end, since those are the most informative sections.
    """
    if len(text) <= max_chars:
        return text

    # Keep 75% from the start (title + abstract + intro + methods)
    # and 25% from the end (conclusion + references context)
    head_size = int(max_chars * 0.75)
    tail_size = max_chars - head_size
    return text[:head_size] + "\n\n[... content truncated for length ...]\n\n" + text[-tail_size:]


# ---------------------------------------------------------------------------
# LLM Summary Generation
# ---------------------------------------------------------------------------

SUMMARIZE_SYSTEM_PROMPT = """You are a research paper analysis expert. Given the full text of a research paper, you produce a comprehensive, structured summary.

You MUST respond with valid JSON only. No markdown fences, no explanation outside the JSON.

The JSON must have this exact structure:
{
  "title": "The exact title of the paper",
  "authors": ["Author Name 1", "Author Name 2"],
  "category": "One of: Language Models, Computer Vision, Reinforcement Learning, Multi-Modal AI, AI Agents, Robotics, Science, Audio & Speech, Reasoning, Generative AI, Safety & Alignment, Efficiency, Other",
  "original_abstract": "The paper's abstract, copied verbatim if found. If not found, write a concise 2-3 sentence abstract.",
  "executive_summary": "A clear, accessible 3-5 paragraph markdown summary of the paper. Use **bold** for key terms. Explain what the paper does, the key innovation, methodology at a high level, and main results. Write for an educated but non-specialist audience.",
  "detailed_breakdown": "A thorough markdown breakdown with sections using ### headings. Include: ### Key Innovation, ### Methodology, ### Architecture & Technical Details, ### Experiments & Results, ### Limitations, ### Impact & Significance. Use bullet points and **bold** for emphasis. Be specific about numbers, benchmarks, and findings."
}

Rules:
- Extract the REAL title and authors from the paper text
- The executive_summary should be 200-400 words, written in clear prose
- The detailed_breakdown should be 400-800 words with specific technical details  
- Use markdown formatting: **bold**, ### headings, - bullet points
- If you cannot identify certain fields (e.g., authors), make your best guess or use "Unknown"
- The category must be one of the listed options
- Be accurate and faithful to the paper's content"""

SUMMARIZE_USER_PROMPT = """Analyze the following research paper text and produce a structured JSON summary.

PAPER TEXT:
{text}

Remember: respond with ONLY a valid JSON object, no other text."""


async def _call_ollama(prompt: str, system_prompt: str) -> str:
    """Call Ollama Cloud API and return the raw text response."""
    cfg = _ollama_config()
    if not cfg["api_key"]:
        raise RuntimeError(
            "OLLAMA_API_KEY is not set. Add it to backend/.env and restart."
        )

    url = f"{cfg['base_url'].rstrip('/')}/api/chat"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "num_predict": 4096,
        },
    }

    logger.info("Calling Ollama Cloud for paper summarization (model=%s)...", cfg["model"])
    start = time.monotonic()

    async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    elapsed = time.monotonic() - start
    logger.info("Ollama summarization completed in %.1fs", elapsed)

    return data.get("message", {}).get("content", "")


def _parse_llm_json(raw: str) -> dict[str, Any]:
    """Parse LLM response as JSON with fallback extraction."""
    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Find first { ... } block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM response as JSON: {raw[:300]}...")


def _slugify(title: str) -> str:
    """Generate a URL-safe slug from a paper title."""
    t = (title or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "untitled-paper"


async def summarize_pdf(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """Full pipeline: extract text from PDF → generate structured summary.
    
    Returns a dict matching the PaperDetail schema shape.
    """
    # 1. Extract text
    raw_text = extract_text_from_pdf(file_bytes)
    if not raw_text or len(raw_text.strip()) < 100:
        raise ValueError(
            "Could not extract sufficient text from the PDF. "
            "The file may be scanned/image-based or corrupted."
        )

    # 2. Truncate for LLM context
    truncated = _truncate_for_context(raw_text, max_chars=12000)

    # 3. Call LLM
    prompt = SUMMARIZE_USER_PROMPT.format(text=truncated)
    raw_response = await _call_ollama(prompt, SUMMARIZE_SYSTEM_PROMPT)

    # 4. Parse response
    result = _parse_llm_json(raw_response)

    # 5. Build paper record
    title = result.get("title", filename.replace(".pdf", "")).strip()
    slug = f"uploaded-{_slugify(title)}"

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    paper = {
        "slug": slug,
        "title": title,
        "authors": result.get("authors", []),
        "category": result.get("category", "Other"),
        "date_published": now.strftime("%B %d, %Y"),
        "time_ago": "just now",
        "read_time_minutes": max(1, len(raw_text.split()) // 200),
        "executive_summary": result.get("executive_summary", ""),
        "detailed_breakdown": result.get("detailed_breakdown", ""),
        "original_abstract": result.get("original_abstract", ""),
        "arxiv_number": None,
        "original_paper_link": None,
        "uploaded": True,
        "uploaded_filename": filename,
    }

    return paper
