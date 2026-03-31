"""
extractor_agent.py — Technical Evidence Extractor agent.
Exact port from multi-agent-research-system-2.
"""

import logging
from crewai import Agent, LLM

from modules.multi_research.tools.pdf_extractor import PDFExtractorTool
from modules.multi_research.tools.web_parser import WebParserTool

logger = logging.getLogger(__name__)


def build_extractor_agent(llm: LLM) -> Agent:
    logger.info("Initialising Evidence Extraction Agent.")

    pdf_tool = PDFExtractorTool()
    web_tool = WebParserTool()

    return Agent(
        role="Technical Evidence Extractor",
        goal=(
            "For each validated source, fetch the content and extract ONLY the "
            "technical core: numeric metrics, dataset names, methodology descriptions, "
            "and up to 2 verbatim quotes. Discard all boilerplate, ads, and navigation "
            "text. Return a JSON array — one object per source — with keys: "
            "source_id, title, url, metrics, datasets, key_findings, quotes. "
            "Never exceed 300 tokens per source object."
        ),
        backstory=(
            "You are a technical analyst specialising in distilling dense research papers "
            "into machine-readable evidence records. You have processed thousands of arXiv "
            "papers and know exactly where to look for the key contribution: the abstract, "
            "the results table, and the conclusion. You never paraphrase carelessly — if "
            "you quote something, it must be verbatim from the source text. If you cannot "
            "find a metric or dataset name, you leave the field empty rather than guessing. "
            "You are ruthlessly concise: your output is used directly in a citation engine "
            "so accuracy beats completeness every time."
        ),
        tools=[pdf_tool, web_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=20,
        max_retry_limit=3,
    )
