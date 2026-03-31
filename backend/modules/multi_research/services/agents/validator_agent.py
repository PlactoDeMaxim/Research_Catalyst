"""
validator_agent.py — Source Quality Evaluator agent.
Exact port from multi-agent-research-system-2.
"""

import logging
from crewai import Agent, LLM

logger = logging.getLogger(__name__)


def build_validator_agent(llm: LLM) -> Agent:
    logger.info("Initialising Source Validator Agent.")
    return Agent(
        role="Research Source Quality Evaluator",
        goal=(
            "Evaluate each source in the provided list and score it from 1–10 based on "
            "credibility, recency, technical depth, and relevance to the research topic. "
            "Return only the top 5 highest-scoring sources as a JSON object. "
            "For each source include the score and a one-sentence rationale."
        ),
        backstory=(
            "You are a peer reviewer with 20 years of experience evaluating research quality "
            "across top-tier ML, NLP, and systems venues. You can instantly distinguish "
            "a genuine academic paper from an SEO-optimised blog post. Your scoring is "
            "rigorous and reproducible: you explicitly check venue reputation, publication "
            "recency, citation signals in the snippet, and whether the source contains "
            "verifiable technical claims rather than vague commentary. You ruthlessly "
            "filter noise — if a source is a listicle or a personal blog without primary "
            "data, it gets a score of 1 and is discarded."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_retry_limit=3,
    )
