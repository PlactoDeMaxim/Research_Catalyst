"""
summary_task.py — Task for the Research Synthesizer Agent.
Exact port from multi-agent-research-system-2.
"""

from crewai import Task


def build_summary_task(synthesizer_agent, extraction_task: Task, topic: str) -> Task:
    return Task(
        description=(
            f"You will receive a JSON array of evidence objects from the Extraction Agent.\n"
            f"The research topic is: '{topic}'\n\n"

            "HARD RULES — violating any of these is a critical failure:\n"
            "  1. ONLY cite sources whose 'url' appears in the evidence array.\n"
            "  2. NEVER add facts that are not present in the evidence.\n"
            "  3. Every factual sentence must end with an inline citation [N].\n"
            "  4. If evidence for a section is absent, omit that section entirely.\n\n"

            "Produce a research summary in the following Markdown structure:\n\n"

            "---\n"
            f"# Research Summary: {topic}\n\n"
            "## Key Insights\n"
            "1. **<Headline>**\n"
            "   <Evidence: 2–4 sentences.>\n"
            "   *Source: [1]*\n\n"
            "2. ...\n\n"
            "## Methodology Overview  *(omit if no methodology evidence)*\n"
            "<Concise description drawn from key_findings.>\n\n"
            "## Benchmarks & Metrics  *(omit if no metrics evidence)*\n"
            "| Metric | Value | Source |\n"
            "|--------|-------|--------|\n"
            "| ...    | ...   | [N]    |\n\n"
            "## Sources\n"
            "[1] <title>\n"
            "    <url>\n\n"
            "[2] ...\n"
            "---\n\n"

            "Formatting rules:\n"
            "  • Minimum 3 Key Insights\n"
            "  • Source index [N] corresponds to position in the evidence array (1-based)\n"
            "  • URLs must be copied verbatim from the evidence — do not paraphrase\n"
            "  • Do not include a 'References' section separate from 'Sources'\n"
        ),
        expected_output=(
            "A complete Markdown research report with sections: "
            "Key Insights (≥3), optional Methodology Overview, "
            "optional Benchmarks & Metrics table, and a numbered Sources list. "
            "All facts cite evidence-list sources only. No hallucinated citations."
        ),
        agent=synthesizer_agent,
        context=[extraction_task],
    )
