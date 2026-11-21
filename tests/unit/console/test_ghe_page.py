"""The "Governed Heritage Engineering" page: the manifesto and the principles, explained (FDN-0004, FDN-0012)."""

from __future__ import annotations

import re
from pathlib import Path

from aistack.console.routing import READING_PATHS, respond
from aistack.contracts.console_link import LAN, ConsoleLink
from aistack.ghe import ARTICLES, FAMILIES, PRINCIPLES, of_family
from aistack.i18n import Language, Languages, translator_for
from aistack.renderers.console.html import render_html
from aistack.renderers.console.pages import GHE_PATH, render_ghe_html

LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))
DOCS = Path(__file__).resolve().parents[3] / "docs" / "00-foundation"


def _registry_rows() -> list[tuple[str, str, str]]:
    text = (DOCS / "FDN-0012-AIStack-Principles-Registry.md").read_text(encoding="utf-8")
    return re.findall(r"(?m)^\| ([A-Z]+-P-\d{3}) \| (.+?) \| (C\d) \|", text)


def _manifesto_articles() -> list[tuple[str, str]]:
    text = (DOCS / "The-Sustainable-Heritage-Manifesto.md").read_text(encoding="utf-8")
    return re.findall(r"(?m)^## Article ([IVX]+) — (.+)$", text)


def test_the_page_lists_the_principles_of_the_registry_in_its_order_with_their_level():
    assert [(pid, level) for pid, _, level in _registry_rows()] == list(PRINCIPLES)


def test_the_english_titles_are_the_registrys():
    t = translator_for("en")

    for pid, title, _ in _registry_rows():
        assert t(f"ghe.principle.{pid}") == title


def test_every_principle_has_a_title_in_each_language():
    for lang in ("fr", "en"):
        t = translator_for(lang)
        assert all(t(f"ghe.principle.{pid}").strip() for pid, _ in PRINCIPLES)


def test_the_page_explains_each_article_of_the_manifesto_under_its_number_and_title():
    articles = _manifesto_articles()
    t = translator_for("en")

    assert len(articles) == ARTICLES == 18

    for index, (number, title) in enumerate(articles, start=1):
        assert t(f"ghe.article_{index:02d}.number") == number
        assert t(f"ghe.article_{index:02d}.title") == title


def test_the_families_cover_every_principle_once():
    assert sum(len(of_family(family)) for family in FAMILIES) == len(PRINCIPLES) == 51


def test_the_french_page_names_the_method_the_articles_and_every_principle():
    page = render_ghe_html("fr", LANGUAGES)

    assert "Governed Heritage Engineering" in page
    assert page.count('class="article"') == 18
    assert all(pid in page for pid, _ in PRINCIPLES)
    assert "La connaissance est l'actif premier" in page
    assert "Dans AIStack :" in page


def test_the_english_page_is_in_english():
    page = render_ghe_html("en", LANGUAGES)

    assert "Knowledge Is the Primary Asset" in page and "In AIStack:" in page
    assert "La connaissance est l'actif premier" not in page


def test_the_page_is_a_reading_page_served_in_both_languages():
    assert GHE_PATH in READING_PATHS

    for lang in ("fr", "en"):
        reply = respond("GET", f"{GHE_PATH}?lang={lang}", None, Path("."), LANGUAGES)

        assert reply.status == 200
        assert b"Governed Heritage Engineering" in reply.body


def test_every_control_of_the_page_has_a_tooltip_or_a_text():
    page = render_ghe_html("fr", LANGUAGES)

    for anchor in re.findall(r"<a [^>]*>", page):
        assert "title=" in anchor


def test_the_console_names_the_page_in_its_own_block_under_the_licence_link():
    link = ConsoleLink(name="Selection UI", description="Sélection", url="http://msi:8181", scope=LAN)

    page = render_html((link,), lang="fr")
    aside = page.split('<aside class="console-aside">', 1)[1].split("</aside>", 1)[0]

    assert 'class="aside-ghe"' in aside
    assert f'href="{GHE_PATH}"' in aside and "Le manifeste et les principes" in aside
    assert aside.index('href="/license"') < aside.index('class="aside-ghe"')
    assert 'title="' in aside.split('class="aside-ghe"', 1)[1].split("</div>", 1)[0]


def test_the_english_console_says_it_in_english():
    link = ConsoleLink(name="Selection UI", description="Sélection", url="http://msi:8181", scope=LAN)

    assert "The manifesto and the principles" in render_html((link,), lang="en")
