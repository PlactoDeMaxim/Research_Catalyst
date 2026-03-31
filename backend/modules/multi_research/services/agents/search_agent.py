"""
search_agent.py — Academic Source Finder agent.
Exact port from multi-agent-research-system-2.
"""

import logging
from crewai import Agent, LLM

from modules.multi_research.tools.search_tool import ExaSearchTool, TavilySearchTool

logger = logging.getLogger(__name__)


def build_search_agent(llm: LLM) -> Agent:
    logger.info("Initialising Search Agent.")

    exa_tool    = ExaSearchTool()
    tavily_tool = TavilySearchTool()

    return Agent(
        role="Academic Source Finder",
        goal=(
            "Execute each research query against the available search APIs and collect "
            "a diverse set of high-quality sources. For each query, retrieve up to 8 "
            "sources. Prefer arXiv papers, IEEE publications, ACL anthology papers, "
            "GitHub repositories, and official project documentation. "
            "Return all results as a single JSON array of structured source objects."
        ),
        backstory=(
            "You are a specialist academic librarian with deep knowledge of scientific "
            "databases, pre-print servers, and open-source repositories. You excel at "
            "combining search terms to find the most relevant and credible sources. "
            "You always prioritise primary sources (papers, official docs, codebases) "
            "over secondary commentary. When one search API is unavailable, you "
            "immediately switch to the backup without complaint."
        ),
        tools=[exa_tool, tavily_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=15,
        max_retry_limit=3,
    )
