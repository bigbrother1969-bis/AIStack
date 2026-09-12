from __future__ import annotations

import json
import re

import pytest

from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.views import ArchitectureView, build_all_views
from aistack.renderers.architecture import html as html_module
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
