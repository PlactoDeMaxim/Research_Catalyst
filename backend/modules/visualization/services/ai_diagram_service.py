"""
AI Diagram Generation Service

Uses LLM (Groq) to generate diagram structures from:
1. Research paper text / methodology descriptions
2. Source code / code repositories

The LLM extracts entities and relationships, returning structured JSON
that is then converted into Mermaid/DOT diagram definitions.
"""

import json
from modules.visualization.services.llm_provider import call_llm_structured
from modules.visualization.models.diagram_model import DiagramFormat, DiagramType
from modules.visualization.services.diagram_generation_service import generate, _generate_mermaid
from modules.visualization.models.diagram_model import DiagramGenerateRequest


# ── Prompt Templates ──

TEXT_TO_DIAGRAM_SYSTEM = """You are a research visualization expert. You analyze research text and extract the key concepts, processes, and relationships to create clear, informative diagrams.

You MUST respond with valid JSON only. No markdown, no explanation, just JSON.

The JSON must have this exact structure:
{
  "title": "A concise title for the diagram",
  "nodes": ["Node Label 1", "Node Label 2", "Node Label 3"],
  "edges": [["Source Node", "Target Node", "optional edge label"], ["Source Node", "Target Node"]],
  "diagram_type": "flowchart"
}

Rules:
- Extract 4-15 meaningful nodes from the text
- Node labels should be SHORT (2-5 words max)
- Edges represent relationships, flow, or dependencies
- Edge labels are optional but helpful
- diagram_type should be one of: flowchart, architecture, sequence, methodology, directed
- For methodology/process text: use flowchart with sequential flow
- For system descriptions: use architecture with component relationships
- For interaction descriptions: use sequence with actor interactions
- Keep it clear and readable — don't overcomplicate"""

TEXT_TO_DIAGRAM_PROMPT = """Analyze the following research text and extract a diagram structure.

TEXT:
{text}

Extract the key concepts, processes, steps, or components and their relationships.
Return a JSON object with: title, nodes (array of strings), edges (array of [source, target, optional_label] arrays), and diagram_type."""


CODE_TO_DIAGRAM_SYSTEM = """You are a software architecture visualization expert. You analyze source code and extract the structural elements to create clear architecture and dependency diagrams.

You MUST respond with valid JSON only. No markdown, no explanation, just JSON.

The JSON must have this exact structure:
{
  "title": "A concise title for the diagram",
  "nodes": ["Component 1", "Component 2", "Component 3"],
  "edges": [["Source", "Target", "optional relationship label"], ["Source", "Target"]],
  "diagram_type": "architecture"
}

Rules:
- Extract classes, functions, modules, or components as nodes
- Node labels should be SHORT (the name of the class/function/module)
- Edges represent: imports, calls, inheritance, composition, data flow
- Edge labels describe the relationship type (e.g., "imports", "calls", "extends", "uses")
- diagram_type should be "architecture" for most code, "directed" for call graphs
- Focus on the MOST IMPORTANT structural relationships
- Keep 5-20 nodes maximum — don't list every tiny function
- Group related items when possible"""

CODE_TO_DIAGRAM_PROMPT = """Analyze the following {language} code and extract its architecture/structure as a diagram.

CODE:
```{language}
{code}
```

Extract the key classes, functions, modules, and their relationships (imports, calls, inheritance, etc).
Return a JSON object with: title, nodes (array of strings), edges (array of [source, target, optional_label] arrays), and diagram_type."""


async def generate_from_text(
    text: str,
    diagram_type: str = "flowchart",
    diagram_format: str = "mermaid",
    title: str = "",
) -> dict:
    """
    Generate a diagram from research text using LLM.

    Args:
        text: Research paper text, methodology, or description
        diagram_type: Desired diagram type
        diagram_format: Output format (mermaid or graphviz)
        title: Optional title override

    Returns:
        Dict with nodes, edges, title, diagram_definition, format
    """
    prompt = TEXT_TO_DIAGRAM_PROMPT.format(text=text[:8000])  # Limit input length
    result = await call_llm_structured(prompt, TEXT_TO_DIAGRAM_SYSTEM)

    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    extracted_title = title or result.get("title", "Research Diagram")
    extracted_type = result.get("diagram_type", diagram_type)

    # Map to DiagramType enum
    type_map = {
        "flowchart": DiagramType.FLOWCHART,
        "architecture": DiagramType.ARCHITECTURE,
        "sequence": DiagramType.SEQUENCE,
        "methodology": DiagramType.METHODOLOGY,
        "directed": DiagramType.DIRECTED,
    }
    d_type = type_map.get(extracted_type, DiagramType.FLOWCHART)
    d_format = DiagramFormat.MERMAID if diagram_format == "mermaid" else DiagramFormat.GRAPHVIZ

    # Generate the diagram definition using existing service
    gen_req = DiagramGenerateRequest(
        type=d_type,
        nodes=nodes,
        edges=edges,
        format=d_format,
        title=extracted_title,
    )
    gen_result = generate(gen_req)

    # Build node objects with IDs for the frontend editor
    node_objects = [
        {"id": f"node-{i}", "label": label, "type": "default"}
        for i, label in enumerate(nodes)
    ]

    # Build edge objects for the frontend editor
    edge_objects = []
    for i, edge in enumerate(edges):
        if len(edge) >= 2:
            src_label = edge[0]
            tgt_label = edge[1]
            edge_label = edge[2] if len(edge) > 2 else ""

            # Find node indices
            src_idx = next((j for j, n in enumerate(nodes) if n == src_label), 0)
            tgt_idx = next((j for j, n in enumerate(nodes) if n == tgt_label), 0)

            edge_objects.append({
                "id": f"edge-{i}",
                "source": f"node-{src_idx}",
                "target": f"node-{tgt_idx}",
                "label": edge_label,
            })

    return {
        "nodes": node_objects,
        "edges": edge_objects,
        "title": extracted_title,
        "diagram_definition": gen_result.diagram_definition,
        "format": d_format.value,
        "diagram_type": d_type.value,
        "ai_generated": True,
    }


async def generate_from_code(
    code: str,
    language: str = "python",
    diagram_type: str = "architecture",
    diagram_format: str = "mermaid",
    title: str = "",
) -> dict:
    """
    Generate a diagram from source code using LLM.

    Args:
        code: Source code string
        language: Programming language
        diagram_type: Desired diagram type
        diagram_format: Output format
        title: Optional title override

    Returns:
        Dict with nodes, edges, title, diagram_definition, format
    """
    prompt = CODE_TO_DIAGRAM_PROMPT.format(
        language=language,
        code=code[:10000],  # Limit input length
    )
    result = await call_llm_structured(prompt, CODE_TO_DIAGRAM_SYSTEM)

    nodes = result.get("nodes", [])
    edges = result.get("edges", [])
    extracted_title = title or result.get("title", f"{language.title()} Architecture")
    extracted_type = result.get("diagram_type", diagram_type)

    type_map = {
        "flowchart": DiagramType.FLOWCHART,
        "architecture": DiagramType.ARCHITECTURE,
        "sequence": DiagramType.SEQUENCE,
        "methodology": DiagramType.METHODOLOGY,
        "directed": DiagramType.DIRECTED,
    }
    d_type = type_map.get(extracted_type, DiagramType.ARCHITECTURE)
    d_format = DiagramFormat.MERMAID if diagram_format == "mermaid" else DiagramFormat.GRAPHVIZ

    gen_req = DiagramGenerateRequest(
        type=d_type,
        nodes=nodes,
        edges=edges,
        format=d_format,
        title=extracted_title,
    )
    gen_result = generate(gen_req)

    node_objects = [
        {"id": f"node-{i}", "label": label, "type": "default"}
        for i, label in enumerate(nodes)
    ]

    edge_objects = []
    for i, edge in enumerate(edges):
        if len(edge) >= 2:
            src_label = edge[0]
            tgt_label = edge[1]
            edge_label = edge[2] if len(edge) > 2 else ""

            src_idx = next((j for j, n in enumerate(nodes) if n == src_label), 0)
            tgt_idx = next((j for j, n in enumerate(nodes) if n == tgt_label), 0)

            edge_objects.append({
                "id": f"edge-{i}",
                "source": f"node-{src_idx}",
                "target": f"node-{tgt_idx}",
                "label": edge_label,
            })

    return {
        "nodes": node_objects,
        "edges": edge_objects,
        "title": extracted_title,
        "diagram_definition": gen_result.diagram_definition,
        "format": d_format.value,
        "diagram_type": d_type.value,
        "ai_generated": True,
    }
