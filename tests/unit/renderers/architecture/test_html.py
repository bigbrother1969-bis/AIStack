from __future__ import annotations

import json
import re

import pytest

from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.views import ArchitectureView, build_all_views
from aistack.renderers.architecture import html as html_module
from aistack.renderers.architecture.html import load_vendored_mermaid_js, render_html
from aistack.renderers.architecture.mermaid import render_mermaid


def node(name: str, category: str = "Cat") -> ServiceNode:
    return ServiceNode(
        name=name, category=category, container=None, status=ServiceStatus.NO_CONTAINER
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
