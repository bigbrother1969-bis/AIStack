"""
`aistack.web.simple_console` (ADR-0033). CN0 : le routeur répond sur
les deux formes, sur les deux écouteurs, exige une session (comme
Architecture et le Health cockpit, ADR-0014 § 5). CN1 : la maquette
(variante C) avec ses quatre jauges à valeurs figées.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.i18n import Language, Languages
from aistack.web.app import create_app
from aistack.web.exposure import Listeners

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
@pytest.mark.parametrize("path", ["/simple", "/simple/"])
def test_signed_out_it_leads_to_sign_in(generated: Path, port: int, path: str):
    """ADR-0014 § 5: no session, no infrastructure status."""

    reply = client(generated, port).get(path)

    assert reply.status_code == 303
    assert reply.headers["location"] == f"/login?next={quote(path, safe='')}"


@pytest.mark.parametrize("port", [PUBLIC_PORT, LAN_PORT])
@pytest.mark.parametrize("path", ["/simple", "/simple/"])
def test_signed_in_the_screen_answers_on_both_listeners(generated: Path, port: int, path: str):
    reply = signed_in(client(generated, port)).get(path)

    assert reply.status_code == 200
    assert "text/html" in reply.headers["content-type"]


def test_the_four_gauges_and_the_advanced_link_are_there(generated: Path):
    body = signed_in(client(generated, LAN_PORT)).get("/simple").text

    for label in ("Sécurité", "Sauvegardes", "Espace disque", "Mises à jour"):
        assert label in body
    # Only the one with an issue shows the AI button (CN1: fixed values).
    assert body.count("Demander à l'IA de régler ça") == 1
    assert "Protégée" in body and "À surveiller" in body and "Suffisant" in body and "À jour" in body
    assert 'href="/console.html"' in body
    assert "Mode avancé (console complète)" in body
