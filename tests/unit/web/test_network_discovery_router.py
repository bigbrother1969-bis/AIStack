"""
*Découverte réseau* inside AIStack's single web application
(`ADR-0012`). The add/remove logic is tested in
`tests/unit/network_discovery/test_usernames.py`; what is tested here
is the route: LAN only, the form read, the file written only when
something changed, the localized outcome carried back.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack.i18n import Language, Languages
from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.yaml import (
    load_network_discovery_yaml,
    save_network_discovery_yaml,
)
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8187
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


@pytest.fixture
def definition(tmp_path: Path) -> Path:
    path = tmp_path / "network_discovery.yml"
    save_network_discovery_yaml(
        NetworkDiscoveryDefinition(
            cidr="192.168.1.0/24",
            ssh_key_path_env="AISTACK_SSH_KEY",
            ssh_usernames=("pi", "pi-hole"),
            ssh_timeout_seconds=3.0,
        ),
        path,
    )

    return path


def client(tmp_path: Path, definition: Path, port: int = LAN_PORT) -> TestClient:
    app = create_app(tmp_path, LISTENERS, LANGUAGES, WebPaths(network_discovery=definition))

    return TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False)


@pytest.mark.parametrize("path", ["/network-discovery", "/network-discovery/"])
def test_the_page_lists_the_declared_names_on_the_lan(tmp_path: Path, definition: Path, path: str):
    reply = client(tmp_path, definition).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert "pi-hole" in reply.text
    assert 'action="/network-discovery/add"' in reply.text
    assert 'action="/network-discovery/remove"' in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/network-discovery"),
        ("GET", "/network-discovery/"),
        ("POST", "/network-discovery/add"),
        ("POST", "/network-discovery/remove"),
    ],
)
def test_nothing_answers_on_the_public_port(
    tmp_path: Path, definition: Path, method: str, path: str
):
    public = client(tmp_path, definition, PUBLIC_PORT)
    before = definition.read_bytes()

    reply = public.request(method, path, data={"username": "intruder"})
    missing = public.request(method, "/no-such-screen")

    assert reply.status_code == 404
    assert reply.content == missing.content
    assert definition.read_bytes() == before


def test_adding_a_name_writes_it_and_says_so(tmp_path: Path, definition: Path):
    reply = client(tmp_path, definition).post(
        "/network-discovery/add?lang=en", data={"username": " admin "}
    )

    assert reply.status_code == 303
    assert reply.headers["location"].startswith("/network-discovery/?status=")
    assert "admin" in reply.headers["location"]
    assert load_network_discovery_yaml(definition).ssh_usernames == ("pi", "pi-hole", "admin")


def test_a_name_already_there_leaves_the_file_untouched(tmp_path: Path, definition: Path):
    before = definition.read_bytes()

    reply = client(tmp_path, definition).post("/network-discovery/add", data={"username": "pi"})

    assert reply.status_code == 303
    assert definition.read_bytes() == before


def test_removing_a_name_writes_the_rest(tmp_path: Path, definition: Path):
    reply = client(tmp_path, definition).post(
        "/network-discovery/remove", data={"username": "pi"}
    )

    assert reply.status_code == 303
    assert load_network_discovery_yaml(definition).ssh_usernames == ("pi-hole",)


def test_the_outcome_is_shown_in_the_chosen_language(tmp_path: Path, definition: Path):
    web = client(tmp_path, definition)
    location = web.post(
        "/network-discovery/remove?lang=en", data={"username": "root"}
    ).headers["location"]

    page = web.get(location + "&lang=en")

    assert page.status_code == 200
    assert "root" in page.text
