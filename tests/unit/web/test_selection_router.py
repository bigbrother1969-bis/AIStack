"""
*Selection* inside AIStack's single web application (`ADR-0012`),
generalized to every content and device (`ADR-0022`, 2026-10-09).

A real, temporary library and target directory: the page scans the
library, saving records the selection only — the host executor applies
it, tested in `tests/unit/sync`. Syncthing's status reader is the one
collaborator replaced; its configuration is never reached (no
`syncthing:` block in the test declaration).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.i18n import Language, Languages
from aistack.selection.yaml import load_selection_yaml
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
PAIR = "music--phone"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    (library / "Artist" / "Album").mkdir(parents=True)
    (library / "Artist" / "Album" / "01 - Track.mp3").write_bytes(b"x" * 1024)
    (library / "Private").mkdir()
    (library / "Private" / "secret.mp3").write_bytes(b"y" * 10)
    (tmp_path / "phone").mkdir()
    (tmp_path / "data").mkdir()

    (tmp_path / "sync.yml").write_text(
        "contents:\n"
        "  music:\n"
        "    title: {fr: Musique, en: Music}\n"
        f"    source: {library}\n"
        "    kind: audio\n"
        "    exclude: [Private]\n"
        "destinations:\n"
        "  phone:\n"
        "    title: {fr: Téléphone, en: Phone}\n"
        "    kind: syncthing\n"
        "    device: PHONE\n"
        "    quota_gb: 1\n"
        "  kindle:\n"
        "    kind: kindle\n"
        "pairs:\n"
        "  music/phone:\n"
        f"    target: {tmp_path / 'phone'}\n"
        "    folder: music-android\n",
        encoding="utf-8",
    )
    (tmp_path / "music_android.yml").write_text(
        "app_id: music_android\n"
        "title: Music Android Selection\n"
        "view_id: media-tree\n"
        f"source_root: {library}\n"
        f"target_root: {tmp_path / 'phone'}\n"
        "selection_file: selections/music-android.yml\n",
        encoding="utf-8",
    )
    return tmp_path


def client(workspace: Path, port: int = LAN_PORT, syncthing: Any = None) -> TestClient:
    app = create_app(
        workspace / "data",
        LISTENERS,
        LANGUAGES,
        WebPaths(
            selection=workspace / "music_android.yml",
            sync=workspace / "sync.yml",
            repository_root=workspace,
        ),
        syncthing=syncthing or (lambda definition: SYNCTHING),
    )
    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


def ids_on(page: str) -> list[str]:
    return re.findall(r'name="selected_ids" value="([^"]+)"', page)


@pytest.mark.parametrize("path", ["/selection", "/selection/"])
def test_the_index_lists_every_content_for_every_syncthing_device(workspace: Path, path: str):
    reply = client(workspace).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert f'href="/selection/{PAIR}/?lang=en"' in reply.text
    assert "Phone" in reply.text and "quota 1 GB" in reply.text
    # The Kindle is tranche 4.2: not offered yet.
    assert "music--kindle" not in reply.text


def test_the_pair_page_shows_the_library_without_what_is_excluded(workspace: Path):
    reply = client(workspace).get(f"/selection/{PAIR}/?lang=en")

    assert reply.status_code == 200
    assert ids_on(reply.text) == ["Artist", "Artist/Album"]
    assert f'action="/selection/{PAIR}/save"' in reply.text
    assert f'fetch("/selection/{PAIR}/syncthing-status")' in reply.text
    assert "Music → Phone" in reply.text


def test_an_unknown_or_not_yet_supported_pair_is_not_found(workspace: Path):
    web = client(workspace)
    assert web.get("/selection/music--nowhere/").status_code == 404
    assert web.get("/selection/music--kindle/").status_code == 404


def test_the_syncthing_half_is_answered_alone(workspace: Path):
    reply = client(workspace).get(f"/selection/{PAIR}/syncthing-status")
    assert reply.status_code == 200
    assert reply.json() == SYNCTHING


def test_saving_records_the_selection_and_writes_nothing_else(workspace: Path):
    web = client(workspace)
    reply = web.post(
        f"/selection/{PAIR}/save?lang=en",
        data={"selected_ids": ["Artist/Album", "Private", "../etc"]},
    )

    assert reply.status_code == 303
    assert reply.headers["location"].startswith(f"/selection/{PAIR}/?status=")
    recorded = load_selection_yaml(workspace / "data" / "sync" / "selections" / f"{PAIR}.yml")
    assert recorded is not None
    # Only directories the page offers are kept.
    assert recorded.selected_ids == ["Artist/Album"]
    assert recorded.metadata["managed_by"] == "sync"
    # The host executor applies; the web application links nothing.
    assert list((workspace / "phone").iterdir()) == []
    assert "two minutes" in web.get(f"/selection/{PAIR}/?lang=en").text


def test_the_old_music_selection_is_read_until_the_first_save(workspace: Path):
    old = workspace / "selections" / "music-android.yml"
    old.parent.mkdir()
    old.write_text(
        "selection_id: music_android\ncatalog_id: music_android-library\n"
        "selected_ids: [Artist]\nmetadata: {}\n",
        encoding="utf-8",
    )
    page = client(workspace).get(f"/selection/{PAIR}/").text
    assert 'value="Artist" checked' in page or re.search(r'value="Artist"[^>]*checked', page)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/selection/"),
        ("GET", f"/selection/{PAIR}/"),
        ("GET", f"/selection/{PAIR}/syncthing-status"),
        ("POST", f"/selection/{PAIR}/save"),
        ("POST", f"/selection/{PAIR}/share"),
    ],
)
def test_nothing_answers_or_writes_on_the_public_port(workspace: Path, method: str, path: str):
    reply = client(workspace, PUBLIC_PORT).request(method, path, data={"selected_ids": ["Artist"]})

    assert reply.status_code == 404
    assert not (workspace / "data" / "sync").exists()


def test_a_missing_syncthing_folder_says_to_create_it_rather_than_unreachable(workspace: Path, monkeypatch):
    from aistack.web import selection

    monkeypatch.setattr(selection, "_folder_state", lambda *a: {"share": {"folder": "aistack-music-phone", "device": "Phone"}, "reshare": False})
    page = client(workspace).get(f"/selection/{PAIR}/?lang=en").text
    assert "to create" in page and 'id="syncthing-body"' not in page
    assert f'action="/selection/{PAIR}/share"' in page


def test_an_existing_folder_can_be_shared_again(workspace: Path, monkeypatch):
    from aistack.web import selection

    monkeypatch.setattr(selection, "_folder_state", lambda *a: {"share": None, "reshare": True})
    page = client(workspace).get(f"/selection/{PAIR}/?lang=en").text
    assert f'action="/selection/{PAIR}/reshare"' in page and "Share again" in page
