from __future__ import annotations

import re

from aistack.architecture.dependency_graph import DependencyGraph
from aistack.renderers.text import escape_text

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def render_dependency_mermaid(graph: DependencyGraph) -> str:
    """
    Render a `DependencyGraph` as Mermaid `flowchart` text — a
    genuinely different diagram from `render_mermaid`'s own, added
    2026-09-12 (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, third
    gap).

    **The one Mermaid renderer in this heritage that draws arrows.**
    `render_mermaid`'s own docstring states why it never has: nothing
    `ArchitectureGraph` carried ever named one service depending on
    another, so drawing an edge there would assert a relationship
    never observed (`ARC-P-012`). That gap is exactly what
    `ComposeProvider`'s new `depends_on:` reading closes — a real
    `-->` here is not asserted, it is the same discipline satisfied
    with evidence that did not exist before.

    **One subgraph per Compose project, containers as plain nodes —
    not services.** This graph is built from `ComposeProjectDependencies`
    (`dependency_graph.py`), not `ArchitectureGraph`/`ServiceNode`: a
    node here is any container the project observed running, whether
    or not `service_categorization.yml` curates it as a service of
    its own (decided with the owner 2026-09-12 — most real edges point
    at uncurated sidecars, `bookstack_db`/`redis`/`gluetun` and the
    like). No status colouring, no click-through — those are facts
    about a *declared service*, and a bare container name here may not
    be one.

    **Deterministic.** `DependencyGraph.projects` is already sorted by
    project name (`build_dependency_graph`); within a project,
    `containers`/`edges` arrive pre-sorted from
    `ComposeRuntimeCatalogBuilder`'s own CSV. Node ids are assigned in
    that same walk order, so the same graph always renders to the
    same text, byte for byte.
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
