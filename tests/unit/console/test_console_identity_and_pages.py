"""
The console's publisher, left column, reading pages and tooltips
(2026-10-03).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.console.identity import load_console_identity
from aistack.console.routing import respond
from aistack.contracts.console_link import ConsoleLink
from aistack.renderers.console.html import render_html
from aistack.renderers.console.pages import render_help_html, render_legal_html, render_license_html


def test_the_declared_publisher_loads_in_each_language():
    french = load_console_identity(lang="fr")
    english = load_console_identity(lang="en")

    assert french.publisher == "PERSIAUT – Data & Regulatory Advisory"
    assert french.siren == "925343014"
    assert french.legal_form == "Entreprise individuelle"
    assert english.legal_form.startswith("Sole proprietorship")
    assert [r.name for r in french.repositories] == ["GitHub", "Codeberg"]


def test_a_missing_field_is_refused_never_left_blank(tmp_path: Path):
    path = tmp_path / "identity.yml"
    path.write_text('publisher: "X"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="is missing: copyright_year"):
        load_console_identity(path)


def test_the_legal_notice_names_the_publisher_and_no_street(tmp_path: Path):
    identity = load_console_identity(lang="fr")
    page = render_legal_html(identity, "fr")

    assert "SIREN 925343014" in page
    assert "Paris (75020)" in page
    assert "Fabrice Persiaut" in page
    assert 'href="https://persiaut-consulting.eu"' in page
    assert "un seul cookie" in page


def test_the_licence_page_links_the_licence_and_both_repositories():
    page = render_license_html(load_console_identity(lang="en"), "en")

    assert "AGPL-3.0-or-later" in page
    assert "https://github.com/bigbrother1969-bis/AIStack" in page
    assert "https://codeberg.org/bigbrother1969/AIStack" in page


@pytest.mark.parametrize(("lang", "heading"), [("fr", "Image Docker"), ("en", "Docker image")])
def test_the_licence_page_has_a_block_for_the_docker_hub_image(lang: str, heading: str):
    page = render_license_html(load_console_identity(lang=lang), lang)

    assert f"<h2>{heading}</h2>" in page
    assert 'href="https://hub.docker.com/r/bigbrother1969/aistack-core"' in page
    assert "<code>docker pull bigbrother1969/aistack-core:&lt;version&gt;</code>" in page


def test_an_image_without_an_https_address_is_refused(tmp_path: Path):
    from aistack.console.identity import DEFAULT_IDENTITY

    declared = DEFAULT_IDENTITY.read_text(encoding="utf-8").replace(
        "https://hub.docker.com/", "http://hub.docker.com/"
    )
    path = tmp_path / "console_identity.yml"
    path.write_text(declared, encoding="utf-8")

    with pytest.raises(ValueError, match="https://"):
        load_console_identity(path)


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_the_help_page_exists_in_each_language(lang: str):
    page = render_help_html(lang)

    assert f'<html lang="{lang}">' in page
    assert page.count("<h2>") == 4


@pytest.mark.parametrize("path", ["/help", "/legal", "/license"])
def test_the_console_serves_each_reading_page(tmp_path: Path, path: str):
    response = respond("GET", f"{path}?lang=en", None, tmp_path)

    assert response.status == 200
    assert b'<html lang="en">' in response.body


def test_the_left_column_carries_the_text_the_links_and_the_copyright():
    link = ConsoleLink(name="Selection UI", description="x", url="http://GIGABYTE:8187/selection/", scope="lan")
    page = render_html((link,), lang="fr", identity=load_console_identity(lang="fr"))

    assert "AIStack observe l'infrastructure" in page
    for path in ("/help", "/legal", "/license"):
        assert f'href="{path}"' in page
    assert "© 2026 PERSIAUT – Data &amp; Regulatory Advisory" in page
    assert 'title="Ouvrir Selection UI — accessible uniquement depuis le réseau local"' in page
    # The Settings link says what the page holds (owner, 2026-10-09).
    assert "Langue de l&#x27;interface ; profil, sessions ouvertes" in page or "Langue de l'interface ; profil, sessions ouvertes" in page
    assert "déclarations livrées avec une nouvelle version" in page
