"""
The console inside AIStack's single web application (`ADR-0012` § 1).

`respond` itself is tested route by route in
`tests/unit/console/test_console_routing.py`; what is tested here is
that the router hands it the request faithfully and copies its answer
onto the wire unchanged, on both listeners.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.i18n import LANGUAGE_COOKIE, Language, Languages
from aistack.web.exposure import Listeners
from aistack.web.app import create_app

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)



def client(generated: Path, port: int) -> TestClient:
    return TestClient(
        create_app(generated, LISTENERS, LANGUAGES),
        base_url=f"http://testserver:{port}",
        follow_redirects=False,
    )


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
def test_a_page_is_served_on_both_listeners(generated: Path, port: int):
    reply = client(generated, port).get("/console.html")

    assert reply.status_code == 200
    assert reply.content == b"<p>console fr</p>"


def test_a_requested_language_is_served_and_remembered(generated: Path):
    reply = signed_in(client(generated, PUBLIC_PORT)).get("/architecture.html?lang=en")

    assert reply.status_code == 200
    assert reply.content == b"<p>architecture en</p>"
    assert reply.headers["set-cookie"].startswith(f"{LANGUAGE_COOKIE}=en;")


def test_the_cookie_reaches_respond(generated: Path):
    web = signed_in(client(generated, PUBLIC_PORT))
    web.cookies.set(LANGUAGE_COOKIE, "en")

    assert web.get("/health.html").content == b"<p>health en</p>"


@pytest.mark.parametrize("page", ["/architecture.html", "/health.html"])
def test_the_pages_describing_the_infrastructure_need_a_session(generated: Path, page: str):
    """ADR-0014 § 5: signed out, they lead to sign-in, and back."""

    reply = client(generated, PUBLIC_PORT).get(f"{page}?lang=en")

    assert reply.status_code == 303
    assert reply.headers["location"] == f"/login?next={quote(page + '?lang=en', safe='')}"
    assert client(generated, PUBLIC_PORT).get("/console.html").status_code == 200


def test_the_root_redirects_to_the_console(generated: Path):
    reply = client(generated, PUBLIC_PORT).get("/?lang=en")

    assert reply.status_code == 302
    assert reply.headers["location"] == "/console.html?lang=en"


def test_settings_is_served(generated: Path):
    reply = client(generated, PUBLIC_PORT).get("/settings?lang=en")

    assert reply.status_code == 200
    assert "text/html" in reply.headers["content-type"]


def test_head_sends_the_headers_without_a_body(generated: Path):
    reply = client(generated, PUBLIC_PORT).head("/console.html")

    assert reply.status_code == 200
    assert reply.content == b""
    assert reply.headers["content-length"] == str(len(b"<p>console fr</p>"))


def test_the_headers_respond_sets_are_kept(generated: Path):
    reply = client(generated, PUBLIC_PORT).get("/console.html")

    assert reply.headers["cache-control"] == "no-cache"
    assert reply.headers["vary"] == "Cookie"
    assert reply.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "target", ["/docker-observation.json", "/history", "/../pyproject.toml", "/nowhere"]
)
def test_nothing_outside_the_closed_list_is_served(generated: Path, target: str):
    reply = client(generated, PUBLIC_PORT).get(target)

    assert reply.status_code == 404
    assert b"{}" not in reply.content


def test_an_unknown_path_is_the_console_s_localized_404(generated: Path):
    reply = client(generated, PUBLIC_PORT).get("/nowhere?lang=en")

    assert reply.status_code == 404
    assert b"Page not found" in reply.content


@pytest.mark.parametrize("target", ["/docs", "/redoc", "/openapi.json"])
def test_the_framework_s_own_descriptions_are_switched_off(generated: Path, target: str):
    assert client(generated, PUBLIC_PORT).get(target).status_code == 404
