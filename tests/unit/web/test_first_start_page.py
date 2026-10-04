"""The guided first start's page and link (ADR-0017 § 4)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aistack.instance.first_start import AUTHENTICATION, FALLBACK_SECRET, INSTANCE, SIGN_IN_SECRETS, Pending
from tests.unit.web.test_rights import LAN_PORT, PUBLIC_PORT, build

EVERYTHING = [
    Pending(INSTANCE, True),
    Pending(AUTHENTICATION, True),
    Pending(SIGN_IN_SECRETS, True),
    Pending(FALLBACK_SECRET, False),
]


def client(tmp_path: Path, items: list[Pending], port: int = PUBLIC_PORT) -> TestClient:
    app = build(tmp_path)
    app.state.first_start = items
    scheme = "https" if port == PUBLIC_PORT else "http"
    return TestClient(app, base_url=f"{scheme}://testserver:{port}", follow_redirects=False)


def test_every_page_leads_to_what_is_left_while_something_required_is_missing(tmp_path: Path):
    web = client(tmp_path, EVERYTHING)

    console = web.get("/console.html?lang=fr").text
    assert 'href="/setup?lang=fr"' in console
    assert "À configurer" in console
    assert 'href="/setup?lang=en"' in web.get("/console.html?lang=en").text


def test_nothing_is_shown_once_everything_required_is_declared(tmp_path: Path):
    web = client(tmp_path, [Pending(FALLBACK_SECRET, False)])

    assert "/setup" not in web.get("/console.html").text


def test_the_page_is_public_and_says_what_where_and_the_values_in_use(tmp_path: Path):
    for port in (PUBLIC_PORT, LAN_PORT):
        page = client(tmp_path, EVERYTHING, port).get("/setup?lang=fr")
        assert page.status_code == 200

    text = page.text
    assert "instance_config.yml" in text and "authentication.yml" in text and ".env.web" in text
    assert "lan_hostname" in text and "GIGABYTE" in text
    assert "AISTACK_OIDC_CLIENT_ID" in text
    assert "/help/manual?lang=fr#avec-docker" in text
    assert "recommandé" in text


def test_the_page_never_shows_a_secret(tmp_path: Path):
    from tests.unit.authentication_fake import CLIENT_SECRET

    text = client(tmp_path, EVERYTHING).get("/setup?lang=en").text

    assert CLIENT_SECRET not in text
    assert "#with-docker" in text


def test_the_manual_has_the_section_the_page_links_to():
    from aistack.renderers.console.pages import render_manual_html

    assert 'id="avec-docker"' in render_manual_html("fr")
    assert 'id="with-docker"' in render_manual_html("en")


def test_with_nothing_left_the_page_says_so(tmp_path: Path):
    text = client(tmp_path, []).get("/setup?lang=en").text

    assert "Everything needed to start is declared." in text
