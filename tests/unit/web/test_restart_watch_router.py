"""
*Relance au démarrage* inside AIStack's web application (ADR-0012,
ADR-0025): a reading screen, LAN only, over what the watch wrote.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.i18n import Language, Languages
from aistack.restart_watch import journal
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))


def client(tmp_path: Path, port: int = LAN_PORT) -> TestClient:
    app = create_app(tmp_path, LISTENERS, LANGUAGES, WebPaths())

    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


@pytest.mark.parametrize("path", ["/restart-watch", "/restart-watch/"])
def test_before_the_watch_has_run_the_page_says_so(tmp_path: Path, path: str):
    reply = client(tmp_path).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert "has written nothing yet" in reply.text
    assert "No decision yet." in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


def test_the_page_shows_who_is_stuck_and_what_was_decided(tmp_path: Path):
    journal.write_state(
        tmp_path,
        {
            "updated_at": "2026-11-15T09:30:00+00:00", "window_open": True, "dry_run": False,
            "stuck": [{"name": "firefly", "reasons": ["unhealthy"], "seen": 1}],
        },
    )
    journal.append(tmp_path, journal.Entry("2026-11-15T09:03:40+00:00", journal.RESTARTED, "qbittorrent", ("stale_network",), "running"))
    journal.append(tmp_path, journal.Entry("2026-11-15T09:04:10+00:00", journal.FAILED, "scrutiny", ("probe_failed",), "still not running after 180 s"))

    reply = client(tmp_path).get("/restart-watch/?lang=en")

    assert "firefly" in reply.text and "healthcheck failing" in reply.text
    assert "window open" in reply.text
    assert reply.text.index("scrutiny") < reply.text.index("qbittorrent")  # newest first
    assert "still not running after 180 s" in reply.text


def test_the_page_is_in_french_too(tmp_path: Path):
    assert "Journal des décisions" in client(tmp_path).get("/restart-watch/?lang=fr").text


def test_nothing_answers_on_the_public_port(tmp_path: Path):
    assert client(tmp_path, PUBLIC_PORT).get("/restart-watch/").status_code == 404
