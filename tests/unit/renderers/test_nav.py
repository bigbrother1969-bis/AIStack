"""
`aistack.renderers.nav` — the strip every page the console serves
carries (ADR-0010).

The way back to the console was missing from Architecture and the
Health cockpit on the first real use (owner, 2026-09-27): a page
reached from the console must lead back to it without the browser's
own Back button, and in the language being read.
"""

from __future__ import annotations

from aistack.i18n import default_languages, translator_for
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
