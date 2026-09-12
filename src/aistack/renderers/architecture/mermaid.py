from __future__ import annotations

import re

from aistack.architecture.graph import ServiceNode
from aistack.architecture.views import ArchitectureView
from aistack.renderers.text import escape_text

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# One line per `ServiceStatus` value (`graph.py` docstring names all
# four) — the class name is `service.status.value` itself, so no
# separate name mapping exists to fall out of sync with the enum.
# Confirmed/observed statuses both read green: the difference between
# `IN_COMPOSE_PROJECT` and `OBSERVED` is already visible from nesting
# (a project subgraph or a loose node), not from colour.
_CLASS_DEFS = (
    "    classDef in_compose_project fill:#dff6dd,stroke:#116329,color:#116329;",
    "    classDef observed fill:#dff6dd,stroke:#116329,color:#116329;",
    "    classDef declared_not_observed fill:#fff1cc,stroke:#7d4e00,"
    "color:#7d4e00,stroke-dasharray: 4 2;",
    "    classDef no_container fill:#f0f0f0,stroke:#666666,color:#666666,"
    "stroke-dasharray: 2 2;",
)


def render_mermaid(view: ArchitectureView) -> str:
    """
    Render one `ArchitectureView` as Mermaid `flowchart` text.

    **No arrows.** Nothing in `ArchitectureGraph` records that one
    service depends on another — only which category it belongs to,
    and, when observed, which Compose project. Drawing an edge here
    would assert a relationship AIStack never observed (ARC-P-012), so
    the only structure this renders is containment: a category
    subgraph holding a project subgraph holding its services, or a
    standalone service node placed directly in its category.

    **Every id carries a running index, not only a slug.** Nothing in
    `ServiceCategorizationDefinition` forbids two categories naming a
    same-titled service, and a slug alone would collide silently in
    that case — Mermaid would silently merge two distinct services
    into one node. The index makes every id unique on its own; the
    slug beside it is what keeps the raw `.mmd` text legible to a
    human reading it directly. Neither survives alone.

    **Deterministic.** Categories, and services within a category,
    are walked in the order `view.graph` already carries — the
    categorization file's own declared order (`views.py`,
    `available_view_names`) — so the same view always renders to the
    same text, byte for byte.
    """

    lines: list[str] = ["flowchart TD", ""]
    lines.extend(_CLASS_DEFS)
    lines.append("")

    service_index = 0
    project_index = 0
    click_lines: list[str] = []

    for category_index, category in enumerate(view.graph.categories):
        category_id = f"cat_{category_index}_{_slug(category.name)}"
        lines.append(f'    subgraph {category_id}["{escape_text(category.name)}"]')

        project_ids: dict[str, str] = {}
        project_members: dict[str, list[ServiceNode]] = {}
        standalone: list[ServiceNode] = []

        for service in category.services:
            project = service.compose_project

            if project is None:
                standalone.append(service)
                continue

            if project not in project_ids:
                project_ids[project] = f"proj_{project_index}_{_slug(project)}"
                project_members[project] = []
                project_index += 1

            project_members[project].append(service)

        for project, project_id in project_ids.items():
            lines.append(f'        subgraph {project_id}["{escape_text(project)}"]')

            for service in project_members[project]:
                lines.append(f"            {_service_line(service, service_index)}")
                click_line = _click_line(service, service_index)
                if click_line is not None:
                    click_lines.append(click_line)
                service_index += 1

            lines.append("        end")

        for service in standalone:
            lines.append(f"        {_service_line(service, service_index)}")
            click_line = _click_line(service, service_index)
            if click_line is not None:
                click_lines.append(click_line)
            service_index += 1

        lines.append("    end")

    if click_lines:
        lines.append("")
        lines.extend(click_lines)

    return "\n".join(lines) + "\n"


def _node_id(service: ServiceNode, index: int) -> str:
    return f"svc_{index}_{_slug(service.name)}"


def _service_line(service: ServiceNode, index: int) -> str:
    node_id = _node_id(service, index)
    label = escape_text(service.name)

    if service.container:
        label += f"<br/><small>{escape_text(service.container)}</small>"

    return f'{node_id}["{label}"]:::{service.status.value}'


def _click_line(service: ServiceNode, index: int) -> str | None:
    """
    One `click <id> href "<url>" "<tooltip>" _blank` directive per
    service that declares an `href` — added 2026-09-12
    (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10). `None` when the
    service has no `href`, the same "nothing to add" convention
    `ServiceNode.compose_project` already uses for a status that has
    nothing to name.

    **`_blank`, always.** Every `href` this heritage declares points
    at another homelab service, never at a page a link inside this
    Mermaid diagram would otherwise navigate away from and lose;
    opening a new tab keeps `architecture.html` itself in place.

    **Tooltip falls back to the service's own name** when
    `description` is absent, rather than to an empty string — a click
    target with no tooltip at all reads as a Mermaid rendering defect
    before it reads as "this service has no description."
    """

    if not service.href:
        return None

    node_id = _node_id(service, index)
    tooltip = service.description or service.name

    return (
        f'    click {node_id} href "{escape_text(service.href)}" '
        f'"{escape_text(tooltip)}" _blank'
    )


def _slug(text: str) -> str:
    slug = _SLUG_RE.sub("_", text.strip().lower()).strip("_")
    return slug or "x"
