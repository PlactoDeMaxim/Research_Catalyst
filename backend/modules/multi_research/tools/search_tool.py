"""
search_tool.py — CrewAI-compatible search tools (Exa + Tavily).
Exact port from multi-agent-research-system-2.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Type

import requests
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
PAPER_DOMAINS = ("arxiv.org", "ieee.org", "acl.org", "aclweb.org", "semanticscholar.org",
                 "papers.nips.cc", "openreview.net", "dl.acm.org", "pubmed.ncbi.nlm.nih.gov")
REPO_DOMAINS   = ("github.com", "gitlab.com", "huggingface.co")
DOC_DOMAINS    = ("docs.", "readthedocs.io", "pytorch.org", "tensorflow.org",
                  "scikit-learn.org", "numpy.org", "scipy.org", "kubernetes.io",
                  "developer.mozilla.org")

JUNK_DOMAINS = ("medium.com", "towardsdatascience.com", "analyticsvidhya.com",
                "machinelearningmastery.com", "kdnuggets.com", "datacamp.com",
                "listicle", "buzzfeed", "quora.com", "reddit.com")


def _classify_source(url: str) -> str:
    url_lower = url.lower()
    if any(d in url_lower for d in PAPER_DOMAINS):
        return "paper"
    if any(d in url_lower for d in REPO_DOMAINS):
        return "repo"
    if any(d in url_lower for d in DOC_DOMAINS):
        return "documentation"
    return "web"


def _is_junk(url: str) -> bool:
    return any(d in url.lower() for d in JUNK_DOMAINS)


# ---------------------------------------------------------------------------
class SourceResult(BaseModel):
    title: str
    url: str
    source_type: str
    published_date: str
    snippet: str


# ---------------------------------------------------------------------------
class _ExaInput(BaseModel):
    query: str = Field(..., description="Academic or technical search query")
    num_results: int = Field(8, description="Number of results to return (max 10)")


class ExaSearchTool(BaseTool):
    name: str = "Exa Academic Search"
    description: str = (
        "Search academic papers, technical repos, and official docs using the Exa neural "
        "search API. Returns structured source metadata. Prefers arXiv, IEEE, ACL, GitHub."
    )
    args_schema: Type[BaseModel] = _ExaInput

    @retry(
        retry=retry_if_exception_type(requests.exceptions.HTTPError),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _run(self, query: str, num_results: int = 8) -> str:
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            return json.dumps({"error": "EXA_API_KEY not set in environment"})

        payload = {
            "query": query,
            "numResults": min(num_results, 10),
            "useAutoprompt": True,
            "type": "neural",
            "contents": {
                "text": {"maxCharacters": 800},
            },
            "includeDomains": list(PAPER_DOMAINS) + list(REPO_DOMAINS),
        }

        resp = requests.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )

        if resp.status_code == 429:
            logger.warning("Exa rate limit hit – retrying with backoff.")
            resp.raise_for_status()

        resp.raise_for_status()
        data = resp.json()

        results: List[Dict[str, Any]] = []
        for item in data.get("results", []):
            url = item.get("url", "")
            if _is_junk(url):
                continue
            results.append(
                SourceResult(
                    title=item.get("title", "Untitled"),
                    url=url,
                    source_type=_classify_source(url),
                    published_date=item.get("publishedDate", "Unknown"),
                    snippet=(item.get("text") or item.get("snippet", ""))[:500],
                ).model_dump()
            )
            time.sleep(0.1)

        logger.info("Exa returned %d usable results for query: %s", len(results), query)
        return json.dumps(results, indent=2)


# ---------------------------------------------------------------------------
class _TavilyInput(BaseModel):
    query: str = Field(..., description="Academic or technical search query")
    num_results: int = Field(8, description="Number of results to return")


class TavilySearchTool(BaseTool):
    name: str = "Tavily Academic Search"
    description: str = (
        "Fallback search tool using the Tavily API. Returns structured source metadata. "
        "Use when Exa results are insufficient."
    )
    args_schema: Type[BaseModel] = _TavilyInput

    @retry(
        retry=retry_if_exception_type(requests.exceptions.HTTPError),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _run(self, query: str, num_results: int = 8) -> str:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return json.dumps({"error": "TAVILY_API_KEY not set in environment"})

        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": min(num_results, 10),
            "include_answer": False,
            "include_raw_content": False,
        }

        resp = requests.post(
            "https://api.tavily.com/search",
            json=payload,
            timeout=20,
        )

        if resp.status_code == 429:
            logger.warning("Tavily rate limit hit – retrying with backoff.")
            resp.raise_for_status()

        resp.raise_for_status()
        data = resp.json()

        results: List[Dict[str, Any]] = []
        for item in data.get("results", []):
            url = item.get("url", "")
            if _is_junk(url):
                continue
            results.append(
                SourceResult(
                    title=item.get("title", "Untitled"),
                    url=url,
                    source_type=_classify_source(url),
                    published_date=item.get("published_date", "Unknown"),
                    snippet=item.get("content", "")[:500],
                ).model_dump()
            )

        logger.info("Tavily returned %d usable results for query: %s", len(results), query)
        return json.dumps(results, indent=2)
