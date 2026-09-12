from __future__ import annotations

import json
import re

import pytest

from aistack.architecture.beszel_reading import BeszelSystemReading
from aistack.architecture.dependency_graph import (
    ComposeProjectDependencies,
    ContainerDependencyEdge,
    DependencyGraph,
)
from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.topology_definition import (
    ExternalNodeDefinition,
    HardwareProfileDefinition,
    InfrastructureTopologyDefinition,
)
from aistack.architecture.views import ArchitectureView, build_all_views
from aistack.renderers.architecture import html as html_module
from aistack.renderers.architecture.dependency_mermaid import render_dependency_mermaid
from aistack.renderers.architecture.html import load_vendored_mermaid_js, render_html
from aistack.renderers.architecture.mermaid import render_mermaid


def node(
    name: str,
    category: str = "Cat",
    *,
    icon: str | None = None,
    href: str | None = None,
    description: str | None = None,
) -> ServiceNode:
    return ServiceNode(
        name=name,
        category=category,
        container=None,
        status=ServiceStatus.NO_CONTAINER,
        icon=icon,
        href=href,
        description=description,
    )


def graph_with_categories(*names: str) -> ArchitectureGraph:
    return ArchitectureGraph(
        categories=tuple(
            CategoryGraph(name=name, services=(node("Svc", name),)) for name in names
        )
    )


def _views_data(document: str) -> dict:
    match = re.search(
        r'<script id="views-data" type="application/json">(.*?)</script>',
        document,
        re.DOTALL,
    )
    assert match, "views-data <script> block not found"
    return json.loads(match.group(1))


# --------------------------------------------------------------------
# Preconditions
# --------------------------------------------------------------------


def test_an_empty_sequence_of_views_is_refused():
    with pytest.raises(ValueError, match="FULL_VIEW"):
        render_html(())


def test_views_not_starting_with_the_full_view_is_refused():
    graph = graph_with_categories("Supervision")
    view = ArchitectureView(name="Supervision", graph=graph)

    with pytest.raises(ValueError, match="FULL_VIEW"):
        render_html((view,))


# --------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------


def test_the_document_is_a_self_contained_html_page():
    views = build_all_views(graph_with_categories("Supervision", "Développement"))

    document = render_html(views)

    assert document.startswith("<!doctype html>")
    assert "<title>AIStack — Architecture</title>" in document
    assert document.strip().endswith("</html>")


def test_the_select_carries_one_option_per_view_full_view_first_and_relabelled():
    views = build_all_views(graph_with_categories("Supervision", "Développement"))

    document = render_html(views)

    assert '<option value="all">Toutes les catégories</option>' in document
    assert '<option value="Supervision">Supervision</option>' in document
    assert '<option value="Développement">Développement</option>' in document
    assert document.index('value="all"') < document.index('value="Supervision"')


def test_the_meta_line_counts_categories_and_services_from_the_full_view():
    views = build_all_views(graph_with_categories("A", "B", "C"))

    document = render_html(views)

    assert "3 catégorie(s), 3 service(s) déclaré(s)" in document


# --------------------------------------------------------------------
# The embedded views data is exactly what render_mermaid produces
# --------------------------------------------------------------------


def test_the_embedded_json_round_trips_to_each_views_own_mermaid_text():
    views = build_all_views(graph_with_categories("Supervision", "Développement"))

    document = render_html(views)
    data = _views_data(document)

    assert set(data) == {view.name for view in views}
    for view in views:
        assert data[view.name] == render_mermaid(view)


def test_a_view_name_containing_a_closing_script_tag_does_not_break_the_embedded_json():
    """
    View names come straight from category names
    (`available_view_names`) and become JSON *keys* without going
    through `escape_text` — unlike service or category labels inside
    the Mermaid text itself, which are always HTML-escaped first
    (`render_mermaid`). A category name is the one value that can
    reach this document with a literal, unescaped `</script>` still
    in it, which is exactly what exercises the `</` -> `<\\/` guard
    in `render_html` rather than `escape_text`'s own.

    `_views_data` itself proves the point: it extracts the
    `views-data` block with a *non-greedy* match up to the first
    `</script`, then `json.loads` it. If this payload's own
    `</script>` had not been escaped, extraction would have
    truncated the JSON text at that point and `json.loads` would
    have raised — it did not, and the key survived intact.
    """

    name = "</script><script>alert(1)</script>"
    graph = ArchitectureGraph(
        categories=(CategoryGraph(name=name, services=(node("Svc", name),)),)
    )
    views = build_all_views(graph)

    document = render_html(views)
    data = _views_data(document)

    assert name in data


# --------------------------------------------------------------------
# The service index (icon + name + link + description) — added
# 2026-09-12, `claude/PLAN-J11-CONSOLE-2026-09-11.md` §10.
# --------------------------------------------------------------------


def test_a_service_with_an_href_is_a_link():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision",
                services=(
                    node(
                        "Pi-hole",
                        "Supervision",
                        href="https://pihole.persiaut-family.fr/admin",
                        description="Gestionnaire de DNS + Blocage de publicités",
                    ),
                ),
            ),
        )
    )

    document = render_html(build_all_views(graph))

    assert (
        '<a href="https://pihole.persiaut-family.fr/admin" target="_blank" '
        'rel="noopener">Pi-hole</a>' in document
    )
    assert "Gestionnaire de DNS + Blocage de publicités" in document


def test_a_service_with_no_href_is_plain_text_not_a_link():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(name="Supervision", services=(node("Pi-hole", "Supervision"),)),
        )
    )

    document = render_html(build_all_views(graph))

    assert "<span>Pi-hole</span>" in document
    assert '<a href="" ' not in document


def test_a_service_with_no_description_carries_no_description_paragraph():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision",
                services=(
                    node(
                        "Pi-hole",
                        "Supervision",
                        href="https://pihole.persiaut-family.fr/admin",
                    ),
                ),
            ),
        )
    )

    document = render_html(build_all_views(graph))

    assert '<p class="service-description">' not in document


def test_the_service_index_is_grouped_by_category_and_lists_every_service():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision", services=(node("Beszel", "Supervision"),)
            ),
            CategoryGraph(
                name="Développement", services=(node("Gitea", "Développement"),)
            ),
        )
    )

    document = render_html(build_all_views(graph))

    assert '<section class="service-index">' in document
    assert "<h3>Supervision</h3>" in document
    assert "<h3>Développement</h3>" in document
    assert document.index("<h3>Supervision</h3>") < document.index("Beszel")
    assert document.index("<h3>Développement</h3>") < document.index("Gitea")


def test_the_service_index_always_reflects_the_full_view_regardless_of_selection():
    """
    `_render_service_index` reads `full.graph.categories` — the view
    at `views[0]`, checked FULL_VIEW at the top of this function —
    not whichever view the caller happens to pass around, so the
    index always lists every category even though the diagram itself
    switches to one category at a time via the `<select>`.
    """

    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision", services=(node("Beszel", "Supervision"),)
            ),
        )
    )

    document = render_html(build_all_views(graph))

    # Only one category exists in this fixture graph, but the point is
    # that the index comes from `views[0]` (the FULL_VIEW), which
    # `build_all_views` always builds with every category present —
    # confirmed by the assertion above already passing for the
    # multi-category fixture.
    assert "Beszel" in document


def test_a_service_with_a_vendored_icon_embeds_it_as_a_data_uri():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision",
                services=(node("Pi-hole", "Supervision", icon="pi-hole"),),
            ),
        )
    )

    document = render_html(build_all_views(graph))

    assert '<img class="service-icon" src="data:image/png;base64,' in document


def test_a_service_with_no_icon_or_an_unknown_icon_gets_the_placeholder():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Supervision",
                services=(
                    node("No Icon", "Supervision"),
                    node("Unknown Icon", "Supervision", icon="does-not-exist"),
                ),
            ),
        )
    )

    document = render_html(build_all_views(graph))

    assert document.count('<span class="service-icon service-icon-none"></span>') == 2


def test_service_index_text_is_escaped():
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Cat",
                services=(
                    node(
                        'Weird & "quoted" <name>',
                        "Cat",
                        href="https://example.test/?a=1&b=2",
                        description='a "quoted" & <b>description</b>',
                    ),
                ),
            ),
        )
    )

    document = render_html(build_all_views(graph))

    assert "&amp;" in document
    assert "&quot;" in document
    assert "&lt;" in document
    assert "&gt;" in document
    assert "<b>description</b>" not in document


# --------------------------------------------------------------------
# The topology section (external nodes + hardware fiches) — added
# 2026-09-12, `claude/PLAN-J11-CONSOLE-2026-09-11.md` §10.
# --------------------------------------------------------------------


def test_no_topology_argument_renders_no_topology_section():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views)

    assert '<section class="topology-index">' not in document


def test_an_entirely_empty_topology_renders_no_section_either():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views, InfrastructureTopologyDefinition())

    assert '<section class="topology-index">' not in document


def test_external_nodes_are_rendered_with_name_role_and_description():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        external_nodes=(
            ExternalNodeDefinition(
                name="OVH",
                role="Registrar de noms de domaine",
                description="Rien n'est hébergé chez OVH.",
            ),
        )
    )

    document = render_html(views, topology)

    assert '<section class="topology-index">' in document
    assert '<span class="topology-name">OVH</span>' in document
    assert (
        '<span class="topology-role">Registrar de noms de domaine</span>'
        in document
    )
    assert "Rien n'est hébergé chez OVH." in document


def test_an_external_node_with_no_description_has_no_description_paragraph():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        external_nodes=(ExternalNodeDefinition(name="Gmail", role="Messagerie"),)
    )

    document = render_html(views, topology)

    assert '<p class="topology-description">' not in document


def test_a_topology_with_only_hardware_renders_only_the_hardware_block():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        hardware=(
            HardwareProfileDefinition(
                name="GIGABYTE",
                model="Gigabyte GA-MA770T-UD3",
                role="Hôte principal",
                cpu="AMD Phenom(tm) II X4 945 Processor",
                ram="16 Go",
                storage="5 disques",
                os_name="LMDE 7",
                gpu="NVIDIA Quadro P400",
            ),
        )
    )

    document = render_html(views, topology)

    assert '<section class="topology-index">' in document
    assert "<h3>Topologie réseau externe</h3>" not in document
    assert "<h3>Fiches matérielles</h3>" in document


def test_a_hardware_profile_renders_all_its_fields():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        hardware=(
            HardwareProfileDefinition(
                name="GIGABYTE",
                model="Gigabyte GA-MA770T-UD3",
                role="Hôte principal, 50+ conteneurs Docker",
                cpu="AMD Phenom(tm) II X4 945 Processor",
                ram="16 Go",
                storage="5 disques",
                os_name="LMDE 7",
                gpu="NVIDIA Quadro P400",
            ),
        )
    )

    document = render_html(views, topology)

    assert "<h4>GIGABYTE</h4>" in document
    assert (
        '<p class="hardware-model">Gigabyte GA-MA770T-UD3</p>' in document
    )
    assert "<dt>CPU</dt><dd>AMD Phenom(tm) II X4 945 Processor</dd>" in document
    assert "<dt>RAM</dt><dd>16 Go</dd>" in document
    assert "<dt>GPU</dt><dd>NVIDIA Quadro P400</dd>" in document
    assert "<dt>Stockage</dt><dd>5 disques</dd>" in document
    assert "<dt>OS</dt><dd>LMDE 7</dd>" in document
    assert "<dt>Rôle</dt><dd>Hôte principal, 50+ conteneurs Docker</dd>" in document


def test_a_hardware_profile_with_no_gpu_has_no_gpu_row():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        hardware=(
            HardwareProfileDefinition(
                name="Raspberry Pi",
                model="Raspberry Pi 3 Model B Rev 1.2",
                role="Reverse proxy",
                cpu="Broadcom BCM2837",
                ram="1 Go",
                storage="Carte micro SD",
                os_name="Debian (aarch64)",
            ),
        )
    )

    document = render_html(views, topology)

    assert "<dt>GPU</dt>" not in document


def test_topology_text_is_escaped():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        external_nodes=(
            ExternalNodeDefinition(
                name='Weird & "quoted" <name>',
                role="a <b>role</b>",
                description='a "quoted" & <b>description</b>',
            ),
        )
    )

    document = render_html(views, topology)

    assert "&amp;" in document
    assert "&quot;" in document
    assert "&lt;" in document
    assert "&gt;" in document
    assert "<b>description</b>" not in document
    assert "<b>role</b>" not in document


def test_both_blocks_render_when_both_are_present():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        external_nodes=(ExternalNodeDefinition(name="Gmail", role="Messagerie"),),
        hardware=(
            HardwareProfileDefinition(
                name="Raspberry Pi",
                model="Raspberry Pi 3 Model B Rev 1.2",
                role="Reverse proxy",
                cpu="Broadcom BCM2837",
                ram="1 Go",
                storage="Carte micro SD",
                os_name="Debian (aarch64)",
            ),
        ),
    )

    document = render_html(views, topology)

    assert document.index("<h3>Topologie réseau externe</h3>") < document.index(
        "<h3>Fiches matérielles</h3>"
    )


# --------------------------------------------------------------------
# The Beszel "État en direct" section — added 2026-09-12,
# `claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, last bullet.
# --------------------------------------------------------------------


def test_no_beszel_readings_renders_no_beszel_section():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views)

    assert '<section class="beszel-index">' not in document


def test_an_empty_tuple_of_readings_renders_no_section_either():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views, None, ())

    assert '<section class="beszel-index">' not in document


def test_a_full_reading_renders_every_field():
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(
        name="Gigabyte",
        host="192.168.1.10",
        status="up",
        cpu_pct=17.42,
        mem_pct=67.74,
        disk_pct=72.22,
        temp_c=68.25,
        load_avg=(0.4, 0.69, 0.87),
        uptime_seconds=241495,
    )

    document = render_html(views, None, (reading,))

    assert '<section class="beszel-index">' in document
    assert "<h4>Gigabyte</h4>" in document
    assert '<p class="beszel-host">192.168.1.10</p>' in document
    assert (
        '<span class="beszel-status beszel-status-up">up</span>' in document
    )
    assert "<dt>CPU</dt><dd>17.4 %</dd>" in document
    assert "<dt>Mémoire</dt><dd>67.7 %</dd>" in document
    assert "<dt>Disque</dt><dd>72.2 %</dd>" in document
    assert "<dt>Température</dt><dd>68.2 °C</dd>" in document
    assert "<dt>Charge</dt><dd>0.40 / 0.69 / 0.87</dd>" in document
    assert "<dt>Disponibilité</dt><dd>2 j 19 h</dd>" in document


def test_a_status_other_than_up_gets_the_other_status_class():
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(name="Pi-hole", host="", status="down")

    document = render_html(views, None, (reading,))

    assert '<span class="beszel-status beszel-status-other">down</span>' in document


def test_an_empty_status_falls_back_to_a_question_mark():
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(name="Pi-hole", host="", status="")

    document = render_html(views, None, (reading,))

    assert '<span class="beszel-status beszel-status-other">?</span>' in document


def test_a_reading_with_no_host_has_no_host_paragraph():
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(name="Pi-hole", host="", status="up")

    document = render_html(views, None, (reading,))

    assert '<p class="beszel-host">' not in document


def test_a_reading_with_every_metric_none_renders_only_the_status_row():
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(name="Pi-hole", host="", status="up")

    document = render_html(views, None, (reading,))

    assert "<dt>CPU</dt>" not in document
    assert "<dt>Mémoire</dt>" not in document
    assert "<dt>Disque</dt>" not in document
    assert "<dt>Température</dt>" not in document
    assert "<dt>Charge</dt>" not in document
    assert "<dt>Disponibilité</dt>" not in document
    assert "<dt>Statut</dt>" in document


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0 min"),
        (59, "0 min"),
        (60, "1 min"),
        (3599, "59 min"),
        (3600, "1 h 0 min"),
        (86399, "23 h 59 min"),
        (86400, "1 j 0 h"),
        (90000, "1 j 1 h"),
    ],
)
def test_uptime_formatting_boundaries(seconds: int, expected: str):
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(
        name="Pi-hole", host="", status="up", uptime_seconds=seconds
    )

    document = render_html(views, None, (reading,))

    assert f"<dt>Disponibilité</dt><dd>{expected}</dd>" in document


def test_several_readings_render_in_order():
    views = build_all_views(graph_with_categories("Supervision"))
    readings = (
        BeszelSystemReading(name="Raspberry pi", host="", status="up"),
        BeszelSystemReading(name="Gigabyte", host="", status="up"),
    )

    document = render_html(views, None, readings)

    assert document.index("Raspberry pi") < document.index("Gigabyte")


def test_beszel_text_is_escaped():
    views = build_all_views(graph_with_categories("Supervision"))
    reading = BeszelSystemReading(
        name='Weird & "quoted" <name>',
        host='a <b>host</b>',
        status="up",
    )

    document = render_html(views, None, (reading,))

    assert "&amp;" in document
    assert "&quot;" in document
    assert "&lt;" in document
    assert "&gt;" in document
    assert "<b>host</b>" not in document


def test_the_beszel_section_comes_after_the_topology_section():
    views = build_all_views(graph_with_categories("Supervision"))
    topology = InfrastructureTopologyDefinition(
        external_nodes=(ExternalNodeDefinition(name="Gmail", role="Messagerie"),),
    )
    reading = BeszelSystemReading(name="Gigabyte", host="", status="up")

    document = render_html(views, topology, (reading,))

    assert document.index('<section class="topology-index">') < document.index(
        '<section class="beszel-index">'
    )


# --------------------------------------------------------------------
# `dependency_graph` — the extra "Dépendances (Docker)" view
# --------------------------------------------------------------------


def _dependency_graph_with_one_edge() -> DependencyGraph:
    return DependencyGraph(
        projects=(
            ComposeProjectDependencies(
                project="bookstack",
                containers=("bookstack", "bookstack_db"),
                edges=(ContainerDependencyEdge("bookstack", "bookstack_db"),),
            ),
        )
    )


def test_no_dependency_graph_argument_adds_no_extra_option():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views)

    assert 'value="dependencies"' not in document
    assert "dependencies" not in _views_data(document)


def test_a_dependency_graph_with_no_projects_adds_no_extra_option():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views, None, (), DependencyGraph())

    assert 'value="dependencies"' not in document
    assert "dependencies" not in _views_data(document)


def test_a_real_dependency_graph_adds_the_dependencies_option():
    views = build_all_views(graph_with_categories("Supervision"))
    dependency_graph = _dependency_graph_with_one_edge()

    document = render_html(views, None, (), dependency_graph)

    assert (
        '<option value="dependencies">Dépendances (Docker)</option>' in document
    )


def test_the_dependencies_option_comes_after_every_view_option():
    views = build_all_views(graph_with_categories("Supervision", "Développement"))
    dependency_graph = _dependency_graph_with_one_edge()

    document = render_html(views, None, (), dependency_graph)

    last_view_option = document.rindex('<option value="Développement">')
    dependencies_option = document.index('value="dependencies"')

    assert dependencies_option > last_view_option


def test_the_embedded_dependencies_definition_matches_render_dependency_mermaid():
    views = build_all_views(graph_with_categories("Supervision"))
    dependency_graph = _dependency_graph_with_one_edge()

    document = render_html(views, None, (), dependency_graph)
    data = _views_data(document)

    assert data["dependencies"] == render_dependency_mermaid(dependency_graph)


def test_a_dependency_view_name_never_collides_with_a_real_category_named_the_same():
    """
    Contrived — no real category is ever named "dependencies" — but
    `render_html` itself only adds the extra option when the name is
    not already a key, so this documents that guard rather than
    assuming it.
    """

    views = build_all_views(graph_with_categories("dependencies"))
    dependency_graph = _dependency_graph_with_one_edge()

    document = render_html(views, None, (), dependency_graph)
    data = _views_data(document)

    assert document.count('value="dependencies"') == 1
    assert data["dependencies"] == render_mermaid(views[1])


# --------------------------------------------------------------------
# The vendored bundle
# --------------------------------------------------------------------


def test_the_vendored_bundle_is_embedded_verbatim():
    views = build_all_views(graph_with_categories("Supervision"))

    document = render_html(views)

    assert load_vendored_mermaid_js() in document


def test_the_vendored_bundle_file_is_the_real_thing():
    js = load_vendored_mermaid_js()

    assert len(js) > 100_000
    assert "mermaid" in js.lower()


def test_the_vendored_bundle_carries_no_script_closing_tag():
    """
    `vendor/PROVENANCE.md` records this as checked against
    mermaid@11.17.2 — this is that check, re-run every time the
    suite runs, so a future upgrade that ever breaks it is caught
    here rather than by a page that silently renders nothing.
    """

    assert "</script" not in load_vendored_mermaid_js().lower()


def test_render_html_refuses_a_vendored_bundle_that_would_truncate_its_tag(
    monkeypatch,
):
    monkeypatch.setattr(
        html_module, "load_vendored_mermaid_js", lambda: "before</script>after"
    )
    views = build_all_views(graph_with_categories("Supervision"))

    with pytest.raises(ValueError, match="script"):
        render_html(views)


# --------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------


def test_rendering_the_same_views_twice_is_byte_identical():
    views = build_all_views(graph_with_categories("Supervision", "Développement"))

    assert render_html(views) == render_html(views)
