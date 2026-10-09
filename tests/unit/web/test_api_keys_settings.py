"""Settings' API keys section (2026-10-09): LAN and administrator only, write-only, tested on request."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack import api_keys
from aistack.api_keys import ApiKey
from aistack.i18n import Language, Languages
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners
from tests.unit.web_signed_in import signed_in

LISTENERS = Listeners(public_port=8183, lan_port=8186)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))
KEY = ApiKey(
    "AISTACK_TEST_ONLY_KEY",
    {"fr": "Clé d'essai", "en": "Test key"},
    {"fr": "Essai", "en": "Test"},
    {"fr": "immédiatement", "en": "immediately"},
    test="gemini",
)


@pytest.fixture(autouse=True)
def clean_environment():
    yield
    os.environ.pop(KEY.name, None)
    api_keys._ORIGINAL.pop(KEY.name, None)


def client(tmp_path: Path, port: int = 8186, tested: list[str] | None = None) -> TestClient:
    def test_key(kind: str) -> str | None:
        if tested is not None:
            tested.append(kind)
        return "" if os.environ.get(KEY.name) == "good-value-1234" else "HTTP 403"

    app = create_app(
        tmp_path, LISTENERS, LANGUAGES, WebPaths(), api_keys=lambda: [KEY], test_api_key=test_key
    )
    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


def csrf(web: TestClient) -> str:
    page = web.get("/settings?lang=en").text
    marker = 'name="csrf" value="'
    start = page.index(marker) + len(marker)
    return page[start : page.index('"', start)]


def test_a_key_entered_is_used_at_once_and_never_shown_again(tmp_path: Path):
    web = client(tmp_path)
    reply = web.post("/settings/api-keys", data={"csrf": csrf(web), "name": KEY.name, "value": "good-value-1234"})

    assert reply.status_code == 303 and "api_key=saved" in reply.headers["location"]
    assert os.environ[KEY.name] == "good-value-1234"
    page = web.get("/settings?lang=en").text
    assert 'id="api-keys"' in page and "…1234" in page and "good-value-1234" not in page
    assert "Entered here" in page


def test_testing_says_whether_the_service_accepts_it(tmp_path: Path):
    tested: list[str] = []
    web = client(tmp_path, tested=tested)
    token = csrf(web)
    web.post("/settings/api-keys", data={"csrf": token, "name": KEY.name, "value": "bad-value-0000"})

    reply = web.post("/settings/api-keys/test", data={"csrf": token, "name": KEY.name})

    assert tested == ["gemini"] and "api_key=test_failed" in reply.headers["location"]
    assert "HTTP 403" in web.get(reply.headers["location"].replace("#api-keys", "")).text


def test_clearing_forgets_the_value(tmp_path: Path):
    web = client(tmp_path)
    token = csrf(web)
    web.post("/settings/api-keys", data={"csrf": token, "name": KEY.name, "value": "good-value-1234"})
    web.post("/settings/api-keys", data={"csrf": token, "name": KEY.name, "clear": "1"})

    assert KEY.name not in os.environ
    assert api_keys.read_store(tmp_path) == {}


def test_an_undeclared_name_is_refused(tmp_path: Path):
    web = client(tmp_path)
    reply = web.post("/settings/api-keys", data={"csrf": csrf(web), "name": "PATH", "value": "x"})
    assert "api_key=unknown" in reply.headers["location"]
    assert api_keys.read_store(tmp_path) == {}


def test_nothing_on_the_public_port(tmp_path: Path):
    web = client(tmp_path, port=8183)
    assert 'id="api-keys"' not in web.get("/settings").text
    assert web.post("/settings/api-keys", data={"name": KEY.name, "value": "x"}).status_code == 404
    assert api_keys.read_store(tmp_path) == {}
