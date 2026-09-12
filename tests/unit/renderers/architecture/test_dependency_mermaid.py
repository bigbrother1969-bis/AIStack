from __future__ import annotations

from aistack.architecture.dependency_graph import (
    ComposeProjectDependencies,
    ContainerDependencyEdge,
    DependencyGraph,
)
from aistack.renderers.architecture.dependency_mermaid import render_dependency_mermaid


def project(
    name: str, containers: tuple[str, ...] = (), edges: tuple[ContainerDependencyEdge, ...] = ()
) -> ComposeProjectDependencies:
    return ComposeProjectDependencies(project=name, containers=containers, edges=edges)


def graph(*projects: ComposeProjectDependencies) -> DependencyGraph:
    return DependencyGraph(projects=tuple(projects))


def test_an_empty_graph_still_renders_the_flowchart_header():
    text = render_dependency_mermaid(graph())

    assert text == "flowchart TD\n\n"


def test_a_project_renders_as_a_subgraph_with_its_containers_as_nodes():
    text = render_dependency_mermaid(
        graph(
            project(
                "bookstack",
                containers=("bookstack", "bookstack_db"),
                edges=(ContainerDependencyEdge("bookstack", "bookstack_db"),),
            )
        )
    )

    assert 'subgraph dep_proj_0_bookstack["bookstack"]' in text
    assert 'dep_0_bookstack["bookstack"]' in text
    assert 'dep_1_bookstack_db["bookstack_db"]' in text
    assert "\n    end" in text


def test_an_edge_is_drawn_between_the_two_container_node_ids():
    text = render_dependency_mermaid(
        graph(
            project(
                "bookstack",
                containers=("bookstack", "bookstack_db"),
                edges=(ContainerDependencyEdge("bookstack", "bookstack_db"),),
            )
        )
    )

    assert "dep_0_bookstack --> dep_1_bookstack_db" in text


def test_edges_are_grouped_after_every_subgraph():
    text = render_dependency_mermaid(
        graph(
            project(
                "bookstack",
                containers=("bookstack", "bookstack_db"),
                edges=(ContainerDependencyEdge("bookstack", "bookstack_db"),),
            )
        )
    )

    subgraph_end = text.rindex("    end")
    edge_line = text.index("dep_0_bookstack --> dep_1_bookstack_db")
    assert edge_line > subgraph_end


def test_a_project_with_no_edges_renders_no_arrow_at_all():
    text = render_dependency_mermaid(graph(project("jellyfin", containers=("jellyfin",))))

    assert "-->" not in text


def test_a_shared_container_name_across_projects_reuses_the_same_node_id():
    """
    Not observed on GIGABYTE (Compose project/container names are
    unique there), but nothing rules it out, and node ids are keyed
    by container name across the whole graph — the second project to
    mention a name reuses the first's id rather than minting a
    duplicate node.
    """

    text = render_dependency_mermaid(
        graph(
            project("a", containers=("shared",)),
            project("b", containers=("shared",), edges=(ContainerDependencyEdge("shared", "shared"),)),
        )
    )

    assert text.count('dep_0_shared["shared"]') == 2
    assert "dep_0_shared --> dep_0_shared" in text


def test_an_edge_naming_a_container_absent_from_any_project_is_dropped():
    """
    `build_dependency_graph` already only carries edges whose target
    was an observed container of that same project (`ARC-P-012`), so
    this should not occur in practice — but the renderer does not
    trust that upstream discipline blindly and drops an edge whose
    endpoint never got a node id, rather than emitting a dangling
    reference into the diagram.
    """

    text = render_dependency_mermaid(
        graph(
            project(
                "odd",
                containers=("a",),
                edges=(ContainerDependencyEdge("a", "ghost"),),
            )
        )
    )

    assert "-->" not in text


def test_project_and_container_names_are_html_escaped():
    text = render_dependency_mermaid(
        graph(project('a & b<c>"d"', containers=('x & y<z>"w"',)))
    )

    assert 'subgraph dep_proj_0_a_b_c_d["a &amp; b&lt;c&gt;&quot;d&quot;"]' in text
    assert 'dep_0_x_y_z_w["x &amp; y&lt;z&gt;&quot;w&quot;"]' in text


def test_node_ids_are_slugified_from_container_names():
    text = render_dependency_mermaid(
        graph(project("My Project!", containers=("My Container!",)))
    )

    assert 'subgraph dep_proj_0_my_project' in text
    assert 'dep_0_my_container[' in text


def test_rendering_is_deterministic_for_the_same_graph():
    same_graph = graph(
        project(
            "bookstack",
            containers=("bookstack", "bookstack_db"),
            edges=(ContainerDependencyEdge("bookstack", "bookstack_db"),),
        )
    )

    assert render_dependency_mermaid(same_graph) == render_dependency_mermaid(same_graph)


def test_two_projects_each_render_their_own_subgraph_in_order():
    text = render_dependency_mermaid(
        graph(
            project("aaa", containers=("a1",)),
            project("zzz", containers=("z1",)),
        )
    )

    assert text.index('subgraph dep_proj_0_aaa') < text.index('subgraph dep_proj_1_zzz')
