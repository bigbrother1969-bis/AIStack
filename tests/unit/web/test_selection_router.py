"""
*Selection UI* inside AIStack's single web application (`ADR-0012`).

A real, temporary music library and target directory: the page scans
the library, saving writes the selection and the hard links for real,
and Syncthing is the only collaborator replaced.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aistack.i18n import Language, Languages
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)

SYNCTHING = {"reachable": True, "state": "idle", "completion": 100.0}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    (library / "Artist" / "Album").mkdir(parents=True)
    (library / "Artist" / "Album" / "01 - Track.mp3").write_bytes(b"x" * 1024)
    (tmp_path / "phone").mkdir()

    (tmp_path / "music_android.yml").write_text(
        "app_id: music_android\n"
        "title: Music Android Selection\n"
        "view_id: media-tree\n"
        f"source_root: {library}\n"
        f"target_root: {tmp_path / 'phone'}\n"
        "selection_file: selections/music-android.yml\n"
        "capacity_declared_bytes: 1000000\n",
        encoding="utf-8",
    )

    return tmp_path


def client(workspace: Path, port: int = LAN_PORT, syncthing: Any = None) -> TestClient:
    app = create_app(
        workspace,
        LISTENERS,
        LANGUAGES,
        WebPaths(selection=workspace / "music_android.yml", repository_root=workspace),
        syncthing=syncthing or (lambda definition: SYNCTHING),
    )

    return TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False)


def ids_on(page: str) -> list[str]:
    return re.findall(r'name="selected_ids" value="([^"]+)"', page)


@pytest.mark.parametrize("path", ["/selection", "/selection/"])
def test_the_page_shows_the_scanned_library(workspace: Path, path: str):
    reply = client(workspace).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert ids_on(reply.text)
    assert 'action="/selection/save"' in reply.text
    assert 'fetch("/selection/syncthing-status")' in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


def test_the_syncthing_half_is_answered_alone(workspace: Path):
    reply = client(workspace).get("/selection/syncthing-status")

    assert reply.status_code == 200
    assert reply.json() == SYNCTHING


def test_an_instance_without_syncthing_answers_null(workspace: Path):
    reply = client(workspace, syncthing=lambda definition: None).get("/selection/syncthing-status")

    assert reply.status_code == 200
    assert reply.json() is None


def test_saving_records_the_selection_and_links_the_files(workspace: Path):
    web = client(workspace)
    assert ids_on(web.get("/selection/").text) == ["Artist", "Artist/Album"]

    reply = web.post("/selection/save?lang=en", data={"selected_ids": ["Artist/Album"]})

    assert reply.status_code == 303
    assert reply.headers["location"].startswith("/selection/?status=")
    assert (workspace / "selections" / "music-android.yml").is_file()
    assert (workspace / "selections" / "music_android-last-generation.yml").is_file()

    linked = [path for path in (workspace / "phone").rglob("*.mp3")]
    assert len(linked) == 1
    assert os.stat(linked[0]).st_ino == os.stat(
        workspace / "library" / "Artist" / "Album" / "01 - Track.mp3"
    ).st_ino


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/selection/"), ("GET", "/selection/syncthing-status"), ("POST", "/selection/save")],
)
def test_nothing_answers_or_writes_on_the_public_port(workspace: Path, method: str, path: str):
    reply = client(workspace, PUBLIC_PORT).request(method, path, data={"selected_ids": ["x"]})

    assert reply.status_code == 404
    assert not (workspace / "selections").exists()
    assert list((workspace / "phone").iterdir()) == []
