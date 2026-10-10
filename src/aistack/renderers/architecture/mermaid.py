from __future__ import annotations

import re

from aistack.architecture.graph import ServiceNode
from aistack.architecture.views import ArchitectureView
from aistack.renderers.text import escape_text

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# One class per `ServiceStatus`, named by its value so no mapping can drift.
# Compose and observed services are both green; nesting in a project
# subgraph already tells them apart.
_CLASS_DEFS = (
    "    classDef in_compose_project fill:#dff6dd,stroke:#116329,color:#116329;",
    "    classDef observed fill:#dff6dd,stroke:#116329,color:#116329;",
    "    classDef declared_not_observed fill:#fff1cc,stroke:#7d4e00,"
    "color:#7d4e00,stroke-dasharray: 4 2;",
    "    classDef no_container fill:#f0f0f0,stroke:#666666,color:#666666,"
    "stroke-dasharray: 2 2;",
)


def render_mermaid(view: ArchitectureView) -> str:
    """Render one `ArchitectureView` as Mermaid `flowchart` text.

    No arrows: the graph records categories and Compose projects, not
    dependencies, so the only structure is containment (category, then
    project, then service). Ids carry a running index as well as a slug
    because two categories may name the same service and Mermaid would
    silently merge colliding ids. Walks the declared order, so output is
    deterministic.
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
    """`click` directive for a service with an `href`, or `None` without one.

    Opens in `_blank` so `architecture.html` stays open. The tooltip falls
    back to the service name, since an empty one looks like a rendering bug.
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
