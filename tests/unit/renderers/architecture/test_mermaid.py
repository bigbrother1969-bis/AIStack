from __future__ import annotations

from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.views import ArchitectureView
from aistack.renderers.architecture.mermaid import escape_text, render_mermaid


def node(
    name: str,
    *,
    category: str = "Cat",
    container: str | None = None,
    status: ServiceStatus = ServiceStatus.NO_CONTAINER,
    compose_project: str | None = None,
) -> ServiceNode:
    return ServiceNode(
        name=name,
        category=category,
        container=container,
        status=status,
        compose_project=compose_project,
    )


def category(name: str, *services: ServiceNode) -> CategoryGraph:
    return CategoryGraph(name=name, services=tuple(services))


def view(*categories: CategoryGraph, name: str = "all") -> ArchitectureView:
    return ArchitectureView(
        name=name, graph=ArchitectureGraph(categories=tuple(categories))
    )


def test_an_empty_graph_still_renders_the_flowchart_header_and_classdefs():
    text = render_mermaid(view())

    assert text.startswith("flowchart TD\n")
    for status in ServiceStatus:
        assert f"classDef {status.value} " in text


def test_an_empty_category_renders_an_empty_subgraph():
    text = render_mermaid(view(category("Empty")))

    assert 'subgraph cat_0_empty["Empty"]' in text
    assert "\n    end" in text


def test_a_standalone_service_with_no_container_carries_no_br_tag():
    text = render_mermaid(view(category("Cat", node("Pi-hole"))))

    assert 'svc_0_pi_hole["Pi-hole"]:::no_container' in text
    assert "<br/>" not in text


def test_a_service_with_a_container_shows_it_on_a_second_line():
    text = render_mermaid(
        view(
            category(
                "Cat",
                node("Nginx Proxy Manager", container="npm", status=ServiceStatus.OBSERVED),
            )
        )
    )

    assert (
        'svc_0_nginx_proxy_manager["Nginx Proxy Manager<br/><small>npm</small>"]'
        ":::observed" in text
    )


def test_each_service_status_maps_to_its_own_class_name():
    for status in ServiceStatus:
        text = render_mermaid(view(category("Cat", node("Svc", status=status))))

        assert f":::{status.value}" in text


def test_a_service_in_a_compose_project_is_nested_in_a_project_subgraph():
    text = render_mermaid(
        view(
            category(
                "Cat",
                node(
                    "Jellyfin",
                    container="jellyfin",
                    status=ServiceStatus.IN_COMPOSE_PROJECT,
                    compose_project="media-stack",
                ),
            )
        )
    )

    lines = text.splitlines()
    project_line = next(i for i, line in enumerate(lines) if "media-stack" in line)
    service_line = next(i for i, line in enumerate(lines) if "Jellyfin" in line)

    assert 'subgraph proj_0_media_stack["media-stack"]' in lines[project_line]
    assert project_line < service_line
    assert lines[service_line].strip().startswith("svc_0_jellyfin")


def test_project_members_are_grouped_even_when_declared_apart():
    """
    Two services of the same project, with an unrelated standalone
    service declared between them in the YAML's own order — the
    grouping is by project membership, not by adjacency in the
    source list.
    """

    text = render_mermaid(
        view(
            category(
                "Cat",
                node(
                    "Radarr",
                    container="radarr",
                    status=ServiceStatus.IN_COMPOSE_PROJECT,
                    compose_project="arr-stack",
                ),
                node("Pi-hole"),
                node(
                    "Sonarr",
                    container="sonarr",
                    status=ServiceStatus.IN_COMPOSE_PROJECT,
                    compose_project="arr-stack",
                ),
            )
        )
    )

    assert text.count('subgraph proj_0_arr_stack["arr-stack"]') == 1
    # Indices are assigned in render order, not in the YAML's own
    # order: both project members (0, 1) come first, and the
    # standalone service declared *between* them in the source list
    # is emitted last, so it gets the trailing index (2).
    assert "svc_0_radarr" in text
    assert "svc_1_sonarr" in text
    assert "svc_2_pi_hole" in text

    project_block = text.split('subgraph proj_0_arr_stack["arr-stack"]')[1].split(
        "\n        end"
    )[0]
    assert "svc_0_radarr" in project_block
    assert "svc_1_sonarr" in project_block
    assert "svc_2_pi_hole" not in project_block


def test_project_subgraphs_render_before_standalone_services():
    text = render_mermaid(
        view(
            category(
                "Cat",
                node("Pi-hole"),
                node(
                    "Jellyfin",
                    container="jellyfin",
                    status=ServiceStatus.IN_COMPOSE_PROJECT,
                    compose_project="media-stack",
                ),
            )
        )
    )

    assert text.index("media-stack") < text.index("Pi-hole")


def test_two_categories_with_a_same_named_service_still_get_distinct_ids():
    """
    Nothing in `ServiceCategorizationDefinition` forbids two categories
    naming a same-titled service — the running index in every id is
    what a slug alone could not guarantee.
    """

    text = render_mermaid(
        view(
            category("Cat A", node("Shared Name")),
            category("Cat B", node("Shared Name")),
        )
    )

    assert "svc_0_shared_name" in text
    assert "svc_1_shared_name" in text
    assert text.count('["Shared Name"]') == 2


def test_categories_and_services_render_in_declared_order():
    text = render_mermaid(
        view(
            category("Zeta", node("Second")),
            category("Alpha", node("First")),
        )
    )

    assert text.index("Zeta") < text.index("Alpha")
    assert text.index("Second") < text.index("First")


def test_rendering_the_same_view_twice_is_byte_identical():
    v = view(category("Cat", node("Pi-hole")))

    assert render_mermaid(v) == render_mermaid(v)


def test_special_characters_in_names_are_escaped():
    text = render_mermaid(
        view(
            category(
                'Cat "A" & <B>',
                node('Weird & "quoted" <name>', container='cont"ainer'),
            )
        )
    )

    assert "&amp;" in text
    assert "&quot;" in text
    assert "&lt;" in text
    assert "&gt;" in text
    assert "<name>" not in text
    assert "<B>" not in text


def test_escape_text_handles_all_four_characters_independently():
    assert escape_text('a & b " c < d > e') == "a &amp; b &quot; c &lt; d &gt; e"
    assert escape_text("plain") == "plain"


def test_a_real_view_from_the_declared_categorization_renders_without_error():
    """
    A regression that loads the real, shipped categorization file —
    not only fixtures — so a typo or an unusual name in the file this
    repository actually ships is caught by this suite rather than
    only discovered when someone opens `architecture.html`.
    """

    from pathlib import Path

    from aistack.architecture.graph import build_architecture_graph
    from aistack.architecture.views import build_all_views
    from aistack.architecture.yaml import load_service_categorization_yaml
    from aistack.kernel.catalog import Catalog

    real_categorization = load_service_categorization_yaml(
        Path(__file__).resolve().parents[4]
        / "src/aistack/architecture/definitions/service_categorization.yml"
    )

    graph = build_architecture_graph(
        real_categorization,
        docker_catalog=Catalog(catalog_id="docker-runtime", title="Docker", items=()),
        compose_catalog=Catalog(catalog_id="compose-runtime", title="Compose", items=()),
    )

    for one_view in build_all_views(graph):
        text = render_mermaid(one_view)
        assert text.startswith("flowchart TD\n")
