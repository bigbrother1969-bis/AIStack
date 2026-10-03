"""
Which port a route answers on (`ADR-0012` § 3, roadmap `R1`).

The routes the console serves are all public, so the LAN-only guard is
exercised on a router built for the test — the same `LAN_ONLY`
dependency every screen's router will carry.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from aistack.web.app import create_app
from aistack.i18n import Language, Languages
from aistack.web.exposure import LAN_ONLY, Listeners, include

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)



def application_with_a_lan_route(generated: Path):
    app = create_app(generated, LISTENERS, LANGUAGES)
    router = APIRouter(dependencies=[LAN_ONLY])

    @router.get("/lan-screen")
    def lan_screen() -> dict[str, str]:
        return {"history": "shown"}

    include(app, router)

    return app


def at(app, port: int) -> TestClient:
    return TestClient(app, base_url=f"http://testserver:{port}")


def test_a_lan_route_answers_on_the_lan_listener(generated: Path):
    reply = at(application_with_a_lan_route(generated), LAN_PORT).get("/lan-screen")

    assert reply.status_code == 200
    assert reply.json() == {"history": "shown"}


def test_a_lan_route_is_refused_on_the_public_listener(generated: Path):
    reply = at(application_with_a_lan_route(generated), PUBLIC_PORT).get("/lan-screen?lang=en")

    assert reply.status_code == 404
    assert b"history" not in reply.content


def test_a_refused_route_reads_exactly_like_a_missing_one(generated: Path):
    public = at(application_with_a_lan_route(generated), PUBLIC_PORT)

    refused = public.get("/lan-screen?lang=en")
    missing = public.get("/no-such-screen?lang=en")

    assert refused.status_code == missing.status_code == 404
    assert refused.content == missing.content


@pytest.mark.parametrize("target", ["/console.html", "/lan-screen"])
def test_a_port_this_application_did_not_declare_is_refused(generated: Path, target: str):
    reply = at(application_with_a_lan_route(generated), 9999).get(target)

    assert reply.status_code == 404
    assert b"console fr" not in reply.content


def test_a_forwarded_header_does_not_open_a_lan_route(generated: Path):
    reply = at(application_with_a_lan_route(generated), PUBLIC_PORT).get(
        "/lan-screen",
        headers={
            "Host": f"GIGABYTE:{LAN_PORT}",
            "X-Forwarded-For": "192.168.1.10",
            "X-Forwarded-Port": str(LAN_PORT),
        },
    )

    assert reply.status_code == 404


def test_one_port_cannot_be_both_listeners():
    with pytest.raises(ValueError, match="share port 8183"):
        Listeners(public_port=8183, lan_port=8183)
