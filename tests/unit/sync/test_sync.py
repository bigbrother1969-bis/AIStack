"""The generalized sync: declarations, the host executor, Syncthing (ADR-0022, 2026-10-09)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.cli import sync_apply
from aistack.kernel.selection.core import Selection
from aistack.selection.yaml import save_selection_yaml
from aistack.sync.declaration import (
    SyncthingAccess,
    folder_for,
    load_sync_declaration,
    mount_point,
    target_for,
)
from aistack.sync.screen import apply_pair, due, read_applied, record_selection, selection_file, waiting
from aistack.sync.syncthing import SyncthingConfig, SyncthingRefused

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def test_the_shipped_declaration_is_gigabytes():
    declaration = load_sync_declaration()
    assert set(declaration.contents) >= {"music", "books", "bd", "comics", "photos", "documents", "films"}
    assert declaration.destinations["phone"].quota_bytes == 64_000_000_000
    assert declaration.contents["documents"].kind == "any"
    assert "restricted" in declaration.contents["documents"].exclude
    # The music keeps its folder: nothing is sent again.
    assert folder_for(declaration, "music", "phone") == "music-android"
    assert str(target_for(declaration, "music", "phone")) == "/media/TechData/Storage/Music-Android"
    assert folder_for(declaration, "books", "latitude") == "aistack-books-latitude"
    assert declaration.syncthing is not None
    assert declaration.syncthing.seen_by_syncthing(Path("/media/BD/.aistack-sync/x")) == "/data/BD/.aistack-sync/x"


def test_a_folder_lives_on_its_contents_own_disk(tmp_path: Path):
    assert mount_point(tmp_path / "a" / "b") == mount_point(tmp_path)
    access = SyncthingAccess(url="u", api_key_env="", path_map=(("/media/TechData", "/x"), ("/media", "/data")))
    assert access.seen_by_syncthing(Path("/media/TechData/M")) == "/x/M"
    assert access.seen_by_syncthing(Path("/media/BD/M")) == "/data/BD/M"
    assert access.seen_by_syncthing(Path("/mediafoo")) == "/mediafoo"


@pytest.fixture
def host(tmp_path: Path) -> tuple[Path, Path]:
    library = tmp_path / "Books"
    (library / "Author" / "Novel").mkdir(parents=True)
    (library / "Author" / "Novel" / "novel.epub").write_bytes(b"e" * 3000)
    (library / "Author" / "Novel" / "cover.jpg").write_bytes(b"j" * 10)
    (library / "Other").mkdir()
    (library / "Other" / "big.pdf").write_bytes(b"p" * 9000)
    (library / "restricted").mkdir()
    (library / "restricted" / "secret.pdf").write_bytes(b"s" * 10)
    config = tmp_path / "sync.yml"
    config.write_text(
        "contents:\n"
        f"  books: {{source: {library}, kind: books, exclude: [restricted]}}\n"
        f"  docs: {{source: {library}, kind: any}}\n"
        "destinations:\n"
        "  phone: {kind: syncthing, device: P, quota_gb: 0.00001}\n"
        # Never the real mount point's `.aistack-sync` in a test.
        "pairs:\n"
        f"  books/phone: {{target: {tmp_path / 'disk' / 'books'}}}\n"
        f"  docs/phone: {{target: {tmp_path / 'disk' / 'docs'}}}\n",
        encoding="utf-8",
    )
    generated = tmp_path / "data"
    generated.mkdir()
    return config, generated


def _select(generated: Path, pair: str, ids: list[str]) -> None:
    save_selection_yaml(Selection(pair, "x", ids, {}), selection_file(generated, pair))


def test_nothing_recorded_is_never_applied(host):
    config, generated = host
    assert not due(generated, "books--phone", NOW)


def test_the_executor_links_the_selection_on_the_same_disk(host):
    config, generated = host
    declaration = load_sync_declaration(config)
    _select(generated, "books--phone", ["Author"])
    assert waiting(generated, "books--phone") and due(generated, "books--phone", NOW)

    record = apply_pair(declaration, generated, "books--phone", NOW)

    target = target_for(declaration, "books", "phone")
    linked = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert linked == ["Author/Novel/novel.epub"]  # books only: no .jpg
    source = config.parent / "Books" / "Author" / "Novel" / "novel.epub"
    assert os.stat(target / linked[0]).st_ino == os.stat(source).st_ino
    assert record["linked"] == 1 and record["selected_bytes"] == 3000 and not record["refused"]
    assert not waiting(generated, "books--phone")
    assert not due(generated, "books--phone", NOW + timedelta(minutes=10))
    assert due(generated, "books--phone", NOW + timedelta(hours=2))

    _select(generated, "books--phone", [])
    os.utime(selection_file(generated, "books--phone"), None)
    assert apply_pair(declaration, generated, "books--phone", NOW)["removed"] == 1
    assert not [p for p in target.rglob("*") if p.is_file()]


def test_the_quota_is_shared_by_the_destinations_contents(host):
    config, generated = host
    declaration = load_sync_declaration(config)  # 10 000 bytes for the phone
    _select(generated, "books--phone", ["Author"])
    apply_pair(declaration, generated, "books--phone", NOW)  # 3 000 taken
    _select(generated, "docs--phone", ["Other"])  # 9 000 more: too much
    record = apply_pair(declaration, generated, "docs--phone", NOW)
    assert "larger than the declared capacity" in record["refused"]
    assert (read_applied(generated, "docs--phone") or {})["selected_bytes"] == 0


def test_the_screen_keeps_only_what_it_offers(host):
    config, generated = host
    declaration = load_sync_declaration(config)
    selection = record_selection(declaration, generated, "books--phone", ["Author", "restricted", "/etc"], "fabrice")
    assert selection.selected_ids == ["Author"]
    assert selection.metadata["saved_by"] == "fabrice"


def test_the_command_applies_what_is_due_and_lists(host, monkeypatch, capsys):
    config, generated = host
    monkeypatch.setattr(sync_apply, "load_sync_declaration", lambda: load_sync_declaration(config))
    monkeypatch.setattr(sync_apply, "data_dir", lambda root: generated)
    _select(generated, "books--phone", ["Author"])

    assert sync_apply.main([]) == 0
    assert "books--phone: +1" in capsys.readouterr().out
    assert sync_apply.main(["--list"]) == 0
    assert "books--phone" in capsys.readouterr().out
    assert sync_apply.main(["nope--phone"]) == 2


def test_syncthing_folders_are_read_and_added_send_only():
    calls: list[tuple[str, str, object]] = []
    folders: list[dict] = [{"id": "music-android"}]

    def call(method: str, path: str, body: bytes | None):
        calls.append((method, path, json.loads(body) if body else None))
        if path == "/rest/config/devices":
            return [{"deviceID": "ZUFNO6Y-AAAA", "name": "latitude"}]
        if path == "/rest/config/folders" and method == "GET":
            return folders
        return None

    config = SyncthingConfig(call)
    assert config.device_id("latitude") == "ZUFNO6Y-AAAA"
    assert config.device_id("ZUFNO6Y") == "ZUFNO6Y-AAAA"
    with pytest.raises(SyncthingRefused):
        config.device_id("unknown")
    assert config.folder("music-android") == {"id": "music-android"}
    assert config.folder("aistack-books-latitude") is None

    config.add_folder("aistack-books-latitude", "Books", "/data/BD/.aistack-sync/latitude/books", "ZUFNO6Y-AAAA")
    method, path, body = calls[-1]
    assert (method, path) == ("POST", "/rest/config/folders")
    assert body == {
        "id": "aistack-books-latitude",
        "label": "Books",
        "path": "/data/BD/.aistack-sync/latitude/books",
        "type": "sendonly",
        "devices": [{"deviceID": "ZUFNO6Y-AAAA"}],
    }
