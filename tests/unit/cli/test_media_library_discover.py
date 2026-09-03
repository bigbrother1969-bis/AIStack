"""
`aistack.cli.media_library_discover` — the on-demand command chosen
2026-09-03 to extend Observation History to the media-library
provider, the same shape as `jellyfin_discover` and
`syncthing_discover`: separate from `selection_ui`'s own
per-page-view call to `MediaLibraryProvider`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.cli import media_library_discover


DEFINITION_YAML = """\
app_id: music_android
title: Music Android Selection
view_id: media-tree
source_root: {source_root}
target_root: /media/does-not-matter-either
selection_file: examples/selections/music-android-selection-real.yml
"""

OBSERVATION = {
    "provider": {"id": "aistack.provider.filesystem.media-library"},
    "collected_at": "2026-09-03T18:00:00+00:00",
    "library": {
        "root": "/media/does-not-matter",
        "exists": True,
        "media_extensions": [".flac", ".mp3"],
        "unreadable": 0,
        "symlinks_not_followed": 0,
        "unrecognized_extensions": {},
        "directories": [],
    },
}


class FakeMediaLibraryProvider:
    def __init__(self, root: Path) -> None:
        self.root = root

    def collect(self) -> dict[str, Any]:
        return OBSERVATION


def _write_definition(path: Path, source_root: Path) -> Path:
    path.write_text(
        DEFINITION_YAML.format(source_root=source_root), encoding="utf-8"
    )
    return path


def test_it_writes_the_observation_and_keeps_history(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        media_library_discover, "MediaLibraryProvider", FakeMediaLibraryProvider
    )

    definition_path = _write_definition(
        tmp_path / "music_android.yml", tmp_path / "library"
    )

    media_library_discover.main(argv=["--definition", str(definition_path)])

    output_path = (
        tmp_path
        / "reports"
        / "generated"
        / "music_android-media-library-observation.json"
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == OBSERVATION

    history_dir = (
        output_path.parent / "history" / "music_android-media-library-observation"
    )
    assert len(list(history_dir.glob("*.json"))) == 1


def test_it_builds_the_provider_against_the_definitions_source_root(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    built: list[Path] = []

    def factory(root: Path):
        built.append(root)
        return FakeMediaLibraryProvider(root)

    monkeypatch.setattr(media_library_discover, "MediaLibraryProvider", factory)

    library_root = tmp_path / "library"
    definition_path = _write_definition(tmp_path / "music_android.yml", library_root)

    media_library_discover.main(argv=["--definition", str(definition_path)])

    assert built == [library_root]


def test_a_second_run_does_not_erase_the_first_observation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        media_library_discover, "MediaLibraryProvider", FakeMediaLibraryProvider
    )

    definition_path = _write_definition(
        tmp_path / "music_android.yml", tmp_path / "library"
    )
    argv = ["--definition", str(definition_path)]

    media_library_discover.main(argv=argv)
    media_library_discover.main(argv=argv)

    output_path = (
        tmp_path
        / "reports"
        / "generated"
        / "music_android-media-library-observation.json"
    )
    history_dir = (
        output_path.parent / "history" / "music_android-media-library-observation"
    )

    assert len(list(history_dir.glob("*.json"))) == 2
