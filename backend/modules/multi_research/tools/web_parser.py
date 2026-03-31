"""
web_parser.py — Webpage text extraction tool for CrewAI.
Exact port from multi-agent-research-system-2.
"""

import logging
import re
from typing import Type

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

HARD_TEXT_LIMIT = 3_000
REQUEST_TIMEOUT = 20

STRIP_TAGS = {
    "script", "style", "noscript", "header", "footer",
    "nav", "aside", "form", "button", "svg", "img",
    "figure", "iframe", "advertisement",
}


class _WebInput(BaseModel):
    url: str = Field(..., description="URL of the webpage or GitHub repo to parse")


class WebParserTool(BaseTool):
    name: str = "Webpage Text Parser"
    description: str = (
        "Fetch a webpage and extract clean, readable text. "
        "Handles documentation sites, arXiv abstracts, and GitHub repositories. "
        "Returns at most 3 000 characters of the primary content."
    )
    args_schema: Type[BaseModel] = _WebInput

    @retry(
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _run(self, url: str) -> str:
        if _is_github_repo_root(url):
            return _fetch_github_readme(url)

        logger.info("Fetching webpage: %s", url)
        resp = requests.get(
            url,
            headers={
                "User-Agent": "ResearchCrew/1.0 (academic crawler)",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(list(STRIP_TAGS)):
            tag.decompose()

        text = _extract_main_content(soup)
        text = _normalise_whitespace(text)
        text = text[:HARD_TEXT_LIMIT]

        logger.info("Webpage parsed: %d chars from %s", len(text), url)
        return text


def _extract_main_content(soup: BeautifulSoup) -> str:
    for selector in [
        "article",
        "main",
        '[role="main"]',
        ".content",
        "#content",
        ".post-content",
        ".entry-content",
    ]:
        element = soup.select_one(selector)
        if element:
            return element.get_text(separator="\n")

    body = soup.find("body")
    return body.get_text(separator="\n") if body else soup.get_text(separator="\n")


def _normalise_whitespace(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return result


def _is_github_repo_root(url: str) -> bool:
    pattern = r"^https?://github\.com/[^/]+/[^/]+/?$"
    return bool(re.match(pattern, url))


def _fetch_github_readme(repo_url: str) -> str:
    match = re.search(r"github\.com/([^/]+/[^/]+)", repo_url)
    if not match:
        return f"Could not parse GitHub repo URL: {repo_url}"

    api_url = f"https://api.github.com/repos/{match.group(1)}/readme"
    headers = {"Accept": "application/vnd.github.v3.raw"}

    try:
        resp = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        text = _normalise_whitespace(resp.text)
        return text[:HARD_TEXT_LIMIT]
    except Exception as exc:
        logger.warning("GitHub README fetch failed for %s: %s", repo_url, exc)
        return f"Could not fetch README for {repo_url}: {exc}"
