"""
LLM-Based Plan Generation Engine

Generates research phases and milestones using Ollama LLM.
Falls back to rule_engine if LLM fails or is unavailable.
"""

from datetime import datetime, timedelta
import uuid
import requests
import json
from typing import Optional

from modules.planner.models.planner_model import Phase, Milestone


# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_TIMEOUT = 180  # seconds


def _distribute_dates(
    start: datetime,
    end: datetime,
    total_milestones: int,
) -> list[str]:
    """Distribute due dates evenly from start to end."""
    if total_milestones <= 0:
        return []
    if total_milestones == 1:
        return [end.strftime("%Y-%m-%d")]

    delta = (end - start) / total_milestones
    return [
        (start + delta * (i + 1)).strftime("%Y-%m-%d")
        for i in range(total_milestones)
    ]


def _build_prompt(topic: str, domain: str, deadline: str) -> str:
    """Build the prompt for the LLM."""
    return f"""You are a research planning assistant.

Given:
Topic: {topic}
Domain: {domain}
Deadline: {deadline}

Generate a structured research plan in STRICT JSON format.

The output must follow this exact schema:

[
  {{
    "title": "Phase Name",
    "description": "Phase description",
    "milestones": [
      {{
        "title": "Milestone Title",
        "description": "Milestone description"
      }}
    ]
  }}
]

Rules:
- Include 4–6 phases.
- Each phase must contain 3 milestones.
- Do NOT include explanations.
- Output ONLY valid JSON.
"""


def generate_plan_with_llm(
    topic: str,
    domain: str,
    deadline: str,
) -> Optional[tuple[list[Phase], list[Milestone]]]:
    """
    Generate a research plan using Ollama LLM.
    
    Returns (phases, milestones) on success, None on failure.
    """
    try:
        # Build prompt
        prompt = _build_prompt(topic, domain, deadline)
        
        # Call Ollama API
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"  # forces JSON mode
            },
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code != 200:
            # print(f"Ollama API error: {response.status_code}")
            return None
        
        # Parse response
        result = response.json()
        # print(f"Raw Ollama result: {result}")
        
        plan_data = json.loads(result["response"])
        # print(f"Parsed plan_data (before extraction): {json.dumps(plan_data, indent=2)}")
        
        # If the response is a dict with a "plan" or "milestones" key, extract it
        if isinstance(plan_data, dict):
            if "plan" in plan_data:
                plan_data = plan_data["plan"]
                # print(f"Extracted plan from 'plan' key")
            elif "milestones" in plan_data:
                plan_data = plan_data["milestones"]
                # print(f"Extracted plan from 'milestones' key")
        
        # Validate structure
        if not isinstance(plan_data, list):
            # print(f"LLM response is not a list. Type: {type(plan_data)}, Value: {plan_data}")
            return None
        
        # Compute dates
        start_date = datetime.now()
        try:
            end_date = datetime.fromisoformat(deadline)
        except (ValueError, TypeError):
            end_date = start_date + timedelta(days=180)  # default: 6 months
        
        # Count total milestones (handle both "milestones" and "tasks" keys)
        total = 0
        for p in plan_data:
            total += len(p.get("milestones", []))
            total += len(p.get("tasks", []))
        dates = _distribute_dates(start_date, end_date, total)
        
        # Convert to Phase and Milestone objects
        phases: list[Phase] = []
        all_milestones: list[Milestone] = []
        date_idx = 0
        
        for p_order, phase_data in enumerate(plan_data):
            phase = Phase(
                title=phase_data.get("title", f"Phase {p_order + 1}"),
                description=phase_data.get("description", ""),
                order=p_order,
                milestones=[],
            )
            
            for m_order, m_data in enumerate(phase_data.get("milestones", [])):
                # Contextualize the milestone description with the topic
                title = m_data.get("title", f"Milestone {m_order + 1}")
                desc = m_data.get("description", "")
                if topic:
                    desc = f"{desc} Topic: {topic}."
                
                milestone = Milestone(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=desc,
                    due_date=dates[date_idx] if date_idx < len(dates) else "",
                    completed=False,
                    phase=phase.title,
                    order=date_idx,
                )
                phase.milestones.append(milestone)
                all_milestones.append(milestone)
                date_idx += 1
            
            # Also handle "tasks" if present (as strings)
            for m_order, task_desc in enumerate(phase_data.get("tasks", [])):
                title = f"Task {m_order + 1}"
                desc = task_desc if isinstance(task_desc, str) else str(task_desc)
                if topic:
                    desc = f"{desc} Topic: {topic}."
                
                milestone = Milestone(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=desc,
                    due_date=dates[date_idx] if date_idx < len(dates) else "",
                    completed=False,
                    phase=phase.title,
                    order=date_idx,
                )
                phase.milestones.append(milestone)
                all_milestones.append(milestone)
                date_idx += 1
            
            phases.append(phase)
        
        return phases, all_milestones
    
    except requests.exceptions.RequestException as e:
        # print(f"Ollama connection error: {e}")
        return None
    except json.JSONDecodeError as e:
        # print(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        # print(f"Unexpected error in LLM generation: {e}")
        return None