from __future__ import annotations

from aistack.renderers.timemachine import ProvenanceNeighbor, render_provenance_mermaid


def neighbor(
    href: str = "/node?iri=urn%3Aaistack%3Aagent%3Aai-reasoning&lang=fr",
    label: str = "ai-reasoning",
    predicate_label: str = "attribué à",
    direction: str = "out",
) -> ProvenanceNeighbor:
    return ProvenanceNeighbor(
        href=href, label=label, predicate_label=predicate_label, direction=direction
    )


def test_a_centre_with_no_neighbors_still_renders_its_own_node():
    text = render_provenance_mermaid("jellyfin", ())

    assert text == (
        "flowchart TD\n\n"
        "    classDef center fill:#dbe9ff,stroke:#1f6feb,color:#0b3d91,"
        "font-weight:bold;\n\n"
        '    node0["jellyfin"]:::center\n'
    )


def test_an_outgoing_neighbor_draws_an_arrow_from_the_centre():
    text = render_provenance_mermaid("jellyfin", (neighbor(direction="out"),))

    assert "node0 -->|attribué à| node1" in text
    assert 'node1["ai-reasoning"]' in text


def test_an_incoming_neighbor_draws_an_arrow_into_the_centre():
    text = render_provenance_mermaid("jellyfin", (neighbor(direction="in"),))

    assert "node1 -->|attribué à| node0" in text


def test_each_neighbor_gets_a_click_line_with_its_own_href_unescaped():
    text = render_provenance_mermaid(
        "jellyfin", (neighbor(href="/node?iri=urn%3Ax&lang=fr"),)
    )

    # The href carries a real "&" between two query params — it must
    # survive verbatim, never turned into "&amp;" (that would corrupt
    # the URL a browser follows on click).
    assert 'click node1 href "/node?iri=urn%3Ax&lang=fr"' in text


def test_click_lines_are_grouped_after_every_node_and_edge():
    text = render_provenance_mermaid("jellyfin", (neighbor(),))

    node_line = text.index('node1["ai-reasoning"]')
    click_line = text.index("click node1")
    assert click_line > node_line


def test_neighbor_and_centre_labels_are_html_escaped():
    text = render_provenance_mermaid(
        'a & b<c>"d"', (neighbor(label='x & y<z>"w"', predicate_label="a & b"),)
    )

    assert 'node0["a &amp; b&lt;c&gt;&quot;d&quot;"]' in text
    assert 'node1["x &amp; y&lt;z&gt;&quot;w&quot;"]' in text
    assert "|a &amp; b|" in text


def test_node_ids_are_assigned_in_the_given_order_starting_after_the_centre():
    text = render_provenance_mermaid(
        "jellyfin",
        (neighbor(label="first"), neighbor(label="second")),
    )

    assert text.index('node1["first"]') < text.index('node2["second"]')


def test_rendering_is_deterministic_for_the_same_input():
    neighbors = (neighbor(),)

    assert render_provenance_mermaid("jellyfin", neighbors) == render_provenance_mermaid(
        "jellyfin", neighbors
    )
