"""
*Priorité CPU* inside AIStack's single web application (`ADR-0012`).
The join and the form are tested in `tests/unit/priority/test_screen.py`;
here, the route: LAN only, Docker replaced by a fake, the definition
read and written where `WebPaths` says.
"""

from __future__ import annotations

from tests.conftest import REFERENCE_DEFINITIONS as REFERENCE

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.i18n import Language, Languages
from aistack.priority.discovery import DiscoveredContainer
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)

DISCOVERED = (
    DiscoveredContainer(name="jellyfin", image="jellyfin/jellyfin", running=True, status="Up 3 days"),
    DiscoveredContainer(name="newcomer", image="busybox", running=True, status="Up 1 minute"),
)


@pytest.fixture
def definition(tmp_path: Path) -> Path:
    path = tmp_path / "resource_priority.yml"
    shutil.copy(REFERENCE / "resource_priority.yml", path)

    return path


def client(tmp_path: Path, definition: Path, port: int = LAN_PORT) -> TestClient:
    app = create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        WebPaths(resource_priority=definition),
        discover=lambda: DISCOVERED,
    )

    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


@pytest.mark.parametrize("path", ["/priority", "/priority/"])
def test_the_page_shows_docker_s_containers_and_the_definition_s(
    tmp_path: Path, definition: Path, path: str
):
    reply = client(tmp_path, definition).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert "newcomer" in reply.text
    assert "sonarr" in reply.text
    assert 'action="/priority/save"' in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


@pytest.mark.parametrize(("method", "path"), [("GET", "/priority/"), ("POST", "/priority/save")])
def test_nothing_answers_or_writes_on_the_public_port(
    tmp_path: Path, definition: Path, method: str, path: str
):
    before = definition.read_bytes()

    reply = client(tmp_path, definition, PUBLIC_PORT).request(
        method, path, data={"classification__newcomer": "priority"}
    )

    assert reply.status_code == 404
    assert definition.read_bytes() == before


def test_saving_writes_what_the_form_describes(tmp_path: Path, definition: Path):
    reply = client(tmp_path, definition).post(
        "/priority/save?lang=en",
        data={
            "classification__jellyfin": "priority",
            "normal_cpus__jellyfin": "3",
            "boosted_cpus__jellyfin": "4",
            "jellyfin_url__jellyfin": "http://127.0.0.1:8096",
            "jellyfin_api_key_env__jellyfin": "JELLYFIN_API_KEY",
            "jellyfin_timeout__jellyfin": "5",
            "classification__newcomer": "throttled",
            "throttled_normal_cpus__newcomer": "",
        },
    )

    assert reply.status_code == 303
    assert reply.headers["location"].startswith("/priority/?status=")

    saved = load_resource_priority_yaml(definition)
    assert [app.container for app in saved.priority] == ["jellyfin"]
    assert [c.name for c in saved.background.containers] == ["newcomer"]
    assert saved.grace_seconds == 60.0


def test_a_docker_that_reports_nothing_still_shows_the_definition(tmp_path: Path, definition: Path):
    app = create_app(
        tmp_path, LISTENERS, LANGUAGES, WebPaths(resource_priority=definition), discover=lambda: ()
    )

    reply = signed_in(TestClient(app, base_url=f"http://testserver:{LAN_PORT}")).get("/priority/")

    assert reply.status_code == 200
    assert "jellyfin" in reply.text
