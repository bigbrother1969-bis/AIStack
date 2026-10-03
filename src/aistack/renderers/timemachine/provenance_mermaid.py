"""
The provenance graph — 1.4's second contribution to the Time Machine
(`ADR-0011` § 19, roadmap `ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.4,
"une vue du graphe"), aligned with the owner's own validated maquette 2
("Suivre les évolutions" — "graphe de provenance centré sur l'étape",
2026-09-27).

**The same mechanism `architecture_render` already vendored, not a new
one.** `aistack.renderers.architecture.dependency_mermaid` already
draws a real, arrowed Mermaid `flowchart` from observed edges
(`ARC-P-012` — an arrow here is never guessed, only an edge the graph
itself carries); the Time Machine's `node` route (`aistack.web.timemachine`) already computes
exactly the two neighbour lists a centred graph needs — `facts`
(outgoing) and `referenced_by` (incoming) — for its existing text
view. This module turns that same, already-computed data into a
Mermaid definition instead of inventing a second graph-layout engine;
the vendored `mermaid.min.js` bundle `architecture.html` already ships
(`aistack.renderers.architecture.html.load_vendored_mermaid_js`) is
reused as-is, not duplicated.

**Deliberately narrower than a full graph browser.** Only one hop from
the centre: the node the owner is looking at, and everything directly
connected to it — exactly what "centré sur l'étape" asks for, not a
whole-graph explorer nobody validated. A caller wanting more hops
follows a neighbour's own click-through, one node at a time — the same
navigation `node.html`'s existing text links already offer.

**Never called with an activity's own instants** — a stream can carry
many, and `node`'s existing route already renders those as their own
chronological list (`instants`), which is the right shape for "every
instant this stream recorded"; folding all of them into this one
node's diagram would clutter "centré sur l'étape" with a concern that
is not about the étape at all. The caller passes only the neighbours
already excluded from that list — `node.html`'s own text view already
makes this exact exclusion (its `wasGeneratedBy` edges of an activity
are shown as `instants`, dropped from `referenced_by`) — this module
does not repeat that filtering, it trusts the caller already did.
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
    """
    One real neighbour of the centre node — a fact the graph itself
    carries, never invented here.

    `href` is a caller-built link (`/node?iri=...&lang=...`, `node`'s
    own route already knows how to build one) — this module draws a
    diagram from already-decided data, the same "hrefs arrive
    pre-built" contract `aistack.renderers.architecture.mermaid`'s own
    `_click_line` already holds for `service.href`, not a router
    itself. **Never passed through `escape_text`**, unlike a label:
    that function turns `&` into `&amp;`, correct for text a browser
    renders but wrong for a URL's own query string (`?iri=...&lang=...`
    genuinely contains `&`) — the caller is trusted to build a safe
    href (`urllib.parse.quote` on the IRI, a `lang` from the closed
    negotiated set), the same way `_click_line` trusts `service.href`.

    `direction` is `"out"` when the centre node is the fact's own
    subject (`node0 --predicate--> neighbour`) and `"in"` when the
    centre is the fact's object (`neighbour --predicate--> node0`) —
    the same subject/object sense `node`'s own `facts`/`referenced_by`
    lists already carry.
    """

    href: str
    label: str
    predicate_label: str
    direction: str  # "out" | "in"


def render_provenance_mermaid(
    center_label: str, neighbors: tuple[ProvenanceNeighbor, ...]
) -> str:
    """
    Render one node and its immediate real neighbours as Mermaid
    `flowchart` text — `node0` is always the centre, `node1`... are
    its neighbours in the order given.

    **Deterministic**: the same `center_label`/`neighbors` always
    renders the same text, byte for byte — the caller is responsible
    for a stable neighbour order (`node`'s own route already builds
    `facts` then `referenced_by` in one fixed walk).
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
