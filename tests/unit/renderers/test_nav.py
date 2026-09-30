"""
`aistack.renderers.nav` — the strip every page the console serves
carries (ADR-0010).

The way back to the console was missing from Architecture and the
Health cockpit on the first real use (owner, 2026-09-27): a page
reached from the console must lead back to it without the browser's
own Back button, and in the language being read.
"""

from __future__ import annotations

from aistack.i18n import Language, Languages, default_languages, translator_for
from aistack.renderers.console.settings import render_settings_html
from aistack.renderers.nav import render_page_nav


def test_the_strip_leads_back_to_the_console_in_the_page_language():
    strip = render_page_nav(translator_for("en"), default_languages(), "en")

    assert '<a class="console-link" href="/console.html?lang=en">' in strip
    assert "← Back to the console" in strip
    assert 'href="/settings"' in strip


def test_the_way_back_comes_first_so_it_sits_on_the_left():
    strip = render_page_nav(translator_for("fr"), default_languages(), "fr")

    assert strip.index("console-link") < strip.index("lang-switch")
    assert strip.index("lang-switch") < strip.index("settings-link")


def test_the_console_itself_offers_no_way_back_to_itself():
    strip = render_page_nav(
        translator_for("fr"), default_languages(), "fr", back_to_console=False
    )

    assert "console-link" not in strip
    assert 'href="/settings"' in strip


def test_the_settings_page_leads_back_to_the_console():
    document = render_settings_html("en", default_languages(), saved=False)

    assert '<a class="console-link" href="/console.html?lang=en">' in document


def test_the_settings_page_declares_a_viewport():
    """
    Added 2026-09-30
    (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constat
    1) — `console.html`'s own audit gap, closed here too since
    Settings is one click away from it.
    """

    document = render_settings_html("en", default_languages(), saved=False)

    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in document


def test_each_language_is_shown_by_its_flag_named_in_its_alt_text():
    strip = render_page_nav(translator_for("fr"), default_languages(), "fr")

    assert '<img class="flag" src="data:image/svg+xml;base64,' in strip
    assert 'alt="English"' in strip
    assert 'title="English"' in strip
    assert 'title="Français" aria-current="true">' in strip


def test_a_language_without_a_flag_is_shown_by_its_name():
    languages = Languages(
        reference="fr",
        available=(Language("fr", "Français"), Language("en", "English")),
    )

    strip = render_page_nav(translator_for("fr"), languages, "fr")

    assert "<img" not in strip
    assert ">English</a>" in strip


# --------------------------------------------------------------------
# `console_base_url` / `extra_query` — added 2026-09-30
# (`claude/AUDIT-CONSOLE-ARCHITECTURE-HEALTH-2026-09-29.md`, constat
# 5): `timemachine_ui` runs on its own port, so its console and
# Settings links must be absolute rather than relative to itself.
# --------------------------------------------------------------------


def test_an_empty_console_base_url_keeps_the_links_relative():
    """The default — every existing caller (console/architecture/
    health/settings) passes nothing here and must see byte-identical
    markup to before this parameter existed."""

    strip = render_page_nav(translator_for("en"), default_languages(), "en")

    assert '<a class="console-link" href="/console.html?lang=en">' in strip
    assert 'href="/settings"' in strip


def test_a_console_base_url_makes_both_links_absolute():
    strip = render_page_nav(
        translator_for("en"),
        default_languages(),
        "en",
        console_base_url="http://GIGABYTE:8183",
    )

    assert (
        '<a class="console-link" href="http://GIGABYTE:8183/console.html?lang=en">'
        in strip
    )
    assert 'href="http://GIGABYTE:8183/settings"' in strip


def test_a_console_base_url_never_touches_the_language_switch():
    """The switch must always stay on the CURRENT page, whichever
    process serves it — only the console/Settings links cross the
    port boundary."""

    strip = render_page_nav(
        translator_for("fr"),
        default_languages(),
        "fr",
        console_base_url="http://GIGABYTE:8183",
    )

    assert 'href="?lang=en"' in strip
    assert 'href="http://GIGABYTE:8183?lang=en"' not in strip


def test_an_empty_extra_query_keeps_the_switch_links_unchanged():
    strip = render_page_nav(translator_for("fr"), default_languages(), "fr")

    assert 'href="?lang=en"' in strip


def test_extra_query_is_appended_to_every_switch_link():
    """`/node`'s own reason to exist: switching language must keep the
    node being read, or the visitor is dropped back to an unparented
    `/node` request."""

    strip = render_page_nav(
        translator_for("fr"),
        default_languages(),
        "fr",
        extra_query="&iri=https%3A%2F%2Fexample.org%2Fa",
    )

    assert 'href="?lang=en&iri=https%3A%2F%2Fexample.org%2Fa"' in strip
