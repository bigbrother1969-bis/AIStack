from __future__ import annotations

from aistack.contracts.console_link import ConsoleLink
from aistack.renderers.console.html import render_html


def selection_ui_link() -> ConsoleLink:
    return ConsoleLink(
        name="Selection UI",
        description="Sélection des candidats",
        url="http://GIGABYTE:8181",
    )


def health_link() -> ConsoleLink:
    return ConsoleLink(
        name="Cockpit Santé", description="Score de santé", url="/health.html"
    )


# --------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------


def test_the_document_is_a_self_contained_html_page():
    document = render_html((selection_ui_link(),))

    assert document.startswith("<!doctype html>")
    assert "<title>AIStack — Console</title>" in document
    assert document.strip().endswith("</html>")


def test_rendering_the_same_links_twice_is_byte_identical():
    links = (selection_ui_link(), health_link())

    assert render_html(links) == render_html(links)


def test_no_external_network_reference_is_present():
    """
    Same discipline `architecture.html`'s vendored mermaid.js and
    `health.html`'s script-free page already hold: this page must
    render correctly with no outbound internet, the normal state of
    the LAN it lives on — no `http(s)://` reference except the
    owner's own declared link targets.
    """

    document = render_html((selection_ui_link(),))

    assert "cdn." not in document
    assert "googleapis" not in document
    assert "<script" not in document


# --------------------------------------------------------------------
# Branding — the owner's own logo, vendored inline
# --------------------------------------------------------------------


def test_the_lockup_is_embedded_as_a_data_uri():
    document = render_html((selection_ui_link(),))

    assert 'src="data:image/png;base64,' in document


def test_the_mark_is_embedded_as_the_favicon():
    document = render_html((selection_ui_link(),))

    assert '<link rel="icon" href="data:image/png;base64,' in document


# --------------------------------------------------------------------
# Links — every declared ConsoleLink becomes one card
# --------------------------------------------------------------------


def test_every_link_becomes_one_card():
    links = (selection_ui_link(), health_link())

    document = render_html(links)

    assert document.count('<a class="card"') == 2
    assert "Selection UI" in document
    assert "Cockpit Santé" in document
    assert 'href="http://GIGABYTE:8181"' in document
    assert 'href="/health.html"' in document


def test_a_links_description_is_shown():
    document = render_html((selection_ui_link(),))

    assert "Sélection des candidats" in document


def test_html_special_characters_in_a_link_are_escaped():
    link = ConsoleLink(
        name="A & B <test>", description="x & y", url="/a?b=1&c=2"
    )

    document = render_html((link,))

    assert "A &amp; B &lt;test&gt;" in document
    assert "x &amp; y" in document
    assert "/a?b=1&amp;c=2" in document
    assert "<test>" not in document


def test_no_links_renders_an_empty_grid_not_an_error():
    document = render_html(())

    assert document.startswith("<!doctype html>")
    assert document.count('<a class="card"') == 0
