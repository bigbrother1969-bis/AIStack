from __future__ import annotations

import re

from aistack.architecture.dependency_graph import DependencyGraph
from aistack.renderers.text import escape_text

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def render_dependency_mermaid(graph: DependencyGraph) -> str:
    """Render a `DependencyGraph` as a Mermaid `flowchart`.

    Unlike `render_mermaid`, this diagram draws arrows: each one comes from
    an observed Compose `depends_on:`. One subgraph per Compose project; nodes
    are containers, not declared services (most edges point at uncurated
    sidecars), so no status colours or links. Output is deterministic: inputs
    arrive sorted and node ids follow that order.
    """

    lines: list[str] = ["flowchart TD", ""]

    node_ids: dict[str, str] = {}
    node_index = 0

    for project_index, project in enumerate(graph.projects):
        project_id = f"dep_proj_{project_index}_{_slug(project.project)}"
        lines.append(f'    subgraph {project_id}["{escape_text(project.project)}"]')

        for container in project.containers:
            if container not in node_ids:
                node_ids[container] = f"dep_{node_index}_{_slug(container)}"
                node_index += 1

            lines.append(f'        {node_ids[container]}["{escape_text(container)}"]')

        lines.append("    end")

    edge_lines: list[str] = []

    for project in graph.projects:
        for edge in project.edges:
            from_id = node_ids.get(edge.from_container)
            to_id = node_ids.get(edge.to_container)

            if from_id is not None and to_id is not None:
                edge_lines.append(f"    {from_id} --> {to_id}")

    if edge_lines:
        lines.append("")
        lines.extend(edge_lines)

    return "\n".join(lines) + "\n"


def _slug(text: str) -> str:
    slug = _SLUG_RE.sub("_", text.strip().lower()).strip("_")
    return slug or "x"
