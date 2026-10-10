"""The Time Machine's provenance graph (ADR-0011 § 19), as Mermaid text.

Draws one node and its direct neighbours (one hop) from the `facts` and
`referenced_by` lists the `node` route in `aistack.web.timemachine`
already computes; deeper navigation goes through each neighbour's link.
Rendered with the `mermaid.min.js` already vendored for
`architecture.html`.

The caller excludes an activity's instants (shown as their own list) and
this module does not filter them again.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.renderers.text import escape_text

_CLASS_DEFS = (
    "    classDef center fill:#dbe9ff,stroke:#1f6feb,color:#0b3d91,"
    "font-weight:bold;",
)


@dataclass(frozen=True)
class ProvenanceNeighbor:
    """One neighbour of the centre node, taken from the graph.

    `href` is built by the caller and is not passed through `escape_text`,
    which would turn the query's `&` into `&amp;`; the caller must build it
    safely (quoted IRI, negotiated `lang`).

    `direction` is `"out"` when the centre is the fact's subject
    (`node0 --predicate--> neighbour`) and `"in"` when it is the object.
    """

    href: str
    label: str
    predicate_label: str
    direction: str  # "out" | "in"


def render_provenance_mermaid(
    center_label: str, neighbors: tuple[ProvenanceNeighbor, ...]
) -> str:
    """Render one node and its neighbours as a Mermaid `flowchart`.

    `node0` is the centre; `node1`... follow the given order, so the output
    is deterministic as long as the caller's order is.
    """

    lines: list[str] = ["flowchart TD", ""]
    lines.extend(_CLASS_DEFS)
    lines.append("")
    lines.append(f'    node0["{escape_text(center_label)}"]:::center')

    click_lines: list[str] = []

    for index, neighbor in enumerate(neighbors, start=1):
        node_id = f"node{index}"
        lines.append(f'    {node_id}["{escape_text(neighbor.label)}"]')

        edge_label = escape_text(neighbor.predicate_label)
        if neighbor.direction == "in":
            lines.append(f"    {node_id} -->|{edge_label}| node0")
        else:
            lines.append(f"    node0 -->|{edge_label}| {node_id}")

        click_lines.append(f'    click {node_id} href "{neighbor.href}"')

    if click_lines:
        lines.append("")
        lines.extend(click_lines)

    return "\n".join(lines) + "\n"
