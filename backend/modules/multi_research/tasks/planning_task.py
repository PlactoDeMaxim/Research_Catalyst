"""
planning_task.py — Task for the Planner Agent.
Exact port from multi-agent-research-system-2.
"""

from crewai import Task


def build_planning_task(planner_agent, topic: str) -> Task:
    return Task(
        description=(
            f"The user wants to research the following topic:\n\n"
            f"    TOPIC: {topic}\n\n"
            "Your job is to decompose this topic into exactly 4–6 highly specific, "
            "actionable search queries. Each query should:\n"
            "  • Target a distinct sub-aspect of the topic (foundation, key methods, "
            "    benchmarks, recent advances, open problems, applications)\n"
            "  • Be formulated as a natural-language string that returns relevant "
            "    results when submitted to arXiv, Semantic Scholar, IEEE Xplore, "
            "    ACL Anthology, or GitHub search\n"
            "  • Avoid repetition — each query must cover unique ground\n\n"
            "DO NOT perform any web searches. Your output is a planning artefact only.\n\n"
            "Return ONLY a valid JSON object — no prose, no markdown fences:\n"
            '{\n  "queries": ["query1", "query2", ...]\n}'
        ),
        expected_output=(
            'A valid JSON object with a single key "queries" containing a list of '
            "4–6 specific search query strings. No extra text, no markdown code fences."
        ),
        agent=planner_agent,
    )
