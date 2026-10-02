"""
Every route says where it answers (`ADR-0012` § 3).

A route without an exposure guard would be served on whichever port
reached it — the public one included. `aistack.web.exposure.include`
refuses a router that does not declare exactly one; this file proves,
over the application exactly as `aistack.web.server` builds it, that
nothing reached the application another way and that every guard
actually runs — by asking every route, with every method it accepts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import Mount, Route

from aistack.web.app import create_app
from aistack.i18n import Language, Languages
from aistack.web.exposure import Listeners
from aistack.web.exposure import LAN_ONLY, PUBLIC, guard_of, serve_on_lan_only

PUBLIC_PORT = 8183
LAN_PORT = 8187
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


UNDECLARED_PORT = 9999


def application(tmp_path: Path) -> FastAPI:
    return create_app(tmp_path, LISTENERS, LANGUAGES)


def every_route(app: FastAPI) -> list[tuple[str, str, object]]:
    """(method, concrete path, guard) for every route of every included router."""

    found = []

    for prefix, router, guard in app.state.routers:
        for route in router.routes:
            assert isinstance(route, APIRoute), route
            path = re.sub(r"\{[^}]+\}", "x", prefix + route.path)

            for method in sorted(route.methods):
                found.append((method, path, guard))

    return found


def test_nothing_reached_the_application_outside_include(tmp_path: Path):
    app = application(tmp_path)

    direct = [route for route in app.routes if isinstance(route, (APIRoute, Route, Mount))]

    assert direct == []
    assert len(app.routes) == len(app.state.routers)


def test_the_application_registers_routes(tmp_path: Path):
    assert every_route(application(tmp_path))


def test_every_route_is_refused_on_a_port_the_application_did_not_declare(tmp_path: Path):
    app = application(tmp_path)
    client = TestClient(app, base_url=f"http://testserver:{UNDECLARED_PORT}")

    answered = {
        (method, path): client.request(method, path).status_code
        for method, path, _ in every_route(app)
    }

    assert {route for route, status in answered.items() if status != 404} == set()


def test_every_lan_route_is_refused_on_the_public_port(tmp_path: Path):
    app = application(tmp_path)
    client = TestClient(app, base_url=f"http://testserver:{PUBLIC_PORT}")

    answered = {
        (method, path): client.request(method, path).status_code
        for method, path, guard in every_route(app)
        if guard is serve_on_lan_only
    }

    assert {route for route, status in answered.items() if status != 404} == set()


def test_a_router_without_an_exposure_is_refused():
    with pytest.raises(ValueError, match="exactly one exposure"):
        guard_of(APIRouter())


def test_a_router_with_two_exposures_is_refused():
    with pytest.raises(ValueError, match="found 2"):
        guard_of(APIRouter(dependencies=[PUBLIC, LAN_ONLY]))
