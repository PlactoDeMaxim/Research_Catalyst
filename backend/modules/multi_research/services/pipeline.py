"""
pipeline.py — Sequential pipeline orchestrator using CrewAI.
Exact port of main.py from multi-agent-research-system-2,
adapted to use Ollama LLM via CrewAI's LLM wrapper.
"""

import logging
import os
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from crewai import Crew, LLM, Process

# Agents
from modules.multi_research.services.agents.planner_agent     import build_planner_agent
from modules.multi_research.services.agents.search_agent      import build_search_agent
from modules.multi_research.services.agents.validator_agent   import build_validator_agent
from modules.multi_research.services.agents.extractor_agent   import build_extractor_agent
from modules.multi_research.services.agents.synthesizer_agent import build_synthesizer_agent

# Tasks
from modules.multi_research.tasks.planning_task    import build_planning_task
from modules.multi_research.tasks.search_task      import build_search_task
from modules.multi_research.tasks.validation_task  import build_validation_task
from modules.multi_research.tasks.extraction_task  import build_extraction_task
from modules.multi_research.tasks.summary_task     import build_summary_task

logger = logging.getLogger(__name__)


def _build_llm() -> LLM:
    """Build a CrewAI LLM instance that uses the Ollama Cloud API.

    CrewAI's LLM class supports Ollama via the 'ollama/' prefix or by
    specifying the base_url. We use the Ollama Cloud endpoint at
    https://ollama.com with the OLLAMA_API_KEY for authentication.
    """
    api_key = os.getenv("OLLAMA_API_KEY", "")
    base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
    model = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))

    logger.info("Using LLM: %s at %s  temperature=%.1f", model, base_url, temperature)

    return LLM(
        model=f"ollama/{model}",
        base_url=f"{base_url.rstrip('/')}",
        api_key=api_key,
        temperature=temperature,
    )


def run_research_pipeline(topic: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> str:
    """Execute the full multi-agent research pipeline for *topic*.

    Parameters
    ----------
    topic:
        The research question or subject to investigate.
    progress_callback:
        Optional callback to receive real-time updates on agent progress.

    Returns
    -------
    str
        The final Markdown research report.
    """
    logger.info("=" * 70)
    logger.info("Starting research pipeline for topic: %s", topic)
    logger.info("=" * 70)
    start_time = time.time()

    # ── Build shared LLM ────────────────────────────────────────────────────
    llm = _build_llm()

    # ── Instantiate agents ──────────────────────────────────────────────────
    logger.info("[1/5] Initialising Planner Agent …")
    planner_agent    = build_planner_agent(llm)

    logger.info("[2/5] Initialising Search Agent …")
    search_agent     = build_search_agent(llm)

    logger.info("[3/5] Initialising Validator Agent …")
    validator_agent  = build_validator_agent(llm)

    logger.info("[4/5] Initialising Extractor Agent …")
    extractor_agent  = build_extractor_agent(llm)

    logger.info("[5/5] Initialising Synthesizer Agent …")
    synthesizer_agent = build_synthesizer_agent(llm)

    # ── Build tasks (chained via context) ───────────────────────────────────
    logger.info("Building task pipeline …")
    planning_task   = build_planning_task(planner_agent, topic)
    search_task     = build_search_task(search_agent, planning_task)
    validation_task = build_validation_task(validator_agent, search_task)
    extraction_task = build_extraction_task(extractor_agent, validation_task)
    summary_task    = build_summary_task(synthesizer_agent, extraction_task, topic)

    if progress_callback:
        planning_task.callback = lambda _: progress_callback({"step": "search", "message": "Planning complete. Search Agent is retrieving sources..."})
        search_task.callback = lambda _: progress_callback({"step": "validate", "message": "Searching complete. Validator Agent is evaluating sources..."})
        validation_task.callback = lambda _: progress_callback({"step": "extract", "message": "Validation complete. Extractor Agent is reading content..."})
        extraction_task.callback = lambda _: progress_callback({"step": "synthesize", "message": "Extraction complete. Synthesizer Agent is writing report..."})

    # ── Assemble the Crew ───────────────────────────────────────────────────
    crew = Crew(
        agents=[
            planner_agent,
            search_agent,
            validator_agent,
            extractor_agent,
            synthesizer_agent,
        ],
        tasks=[
            planning_task,
            search_task,
            validation_task,
            extraction_task,
            summary_task,
        ],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    # ── Execute ─────────────────────────────────────────────────────────────
    if progress_callback:
        progress_callback({"step": "plan", "message": "Planner Agent is determining search queries..."})
        
    logger.info("Kicking off CrewAI pipeline …")
    result = crew.kickoff()

    elapsed = time.time() - start_time
    logger.info("Pipeline completed in %.1f seconds.", elapsed)

    report = str(result)

    # ── Append runtime metadata ─────────────────────────────────────────────
    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    metadata = (
        f"\n\n---\n"
        f"*Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} "
        f"in {elapsed:.0f}s using model `{model_name}`.*\n"
    )
    return report + metadata
