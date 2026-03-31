"""
search_task.py — Task for the Search Agent.
Exact port from multi-agent-research-system-2.
"""

from crewai import Task


def build_search_task(search_agent, planning_task: Task) -> Task:
    return Task(
        description=(
            "You will receive a JSON object from the Planner Agent containing a list "
            "of research queries under the key 'queries'.\n\n"
            "For EACH query in the list:\n"
            "  1. Call the 'Exa Academic Search' tool with the query and num_results=8\n"
            "  2. If Exa returns fewer than 3 results or an error, call "
            "     'Tavily Academic Search' as a fallback\n"
            "  3. Collect all results, removing duplicates (by URL)\n\n"
            "Source quality rules:\n"
            "  • Keep sources from: arXiv, IEEE, ACL, GitHub, official docs\n"
            "  • Discard sources whose URL matches known junk domains "
            "    (Medium, TowardsDataScience, KDNuggets, listicle sites)\n\n"
            "Merge all per-query results into a single flat JSON array.\n\n"
            "Each element must have these exact keys:\n"
            "  title, url, source_type, published_date, snippet\n\n"
            "Return ONLY the JSON array — no prose, no markdown."
        ),
        expected_output=(
            "A JSON array of source objects. Each object has keys: "
            "title, url, source_type (paper|repo|documentation|web), "
            "published_date, snippet. No duplicates. No markdown fences."
        ),
        agent=search_agent,
        context=[planning_task],
    )
