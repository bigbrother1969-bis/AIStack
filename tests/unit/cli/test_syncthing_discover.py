"""
`aistack.cli.syncthing_discover` — the on-demand command chosen
2026-09-03 to extend Observation History to Syncthing, the same
shape as `jellyfin_discover`: separate from `selection_ui`'s own
per-page-view call, which would produce far too many near-duplicate
history files for "keep everything, indefinitely" to have been
decided for.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import syncthing_discover


DEFINITION_YAML = """\
app_id: music_android
title: Music Android Selection
view_id: media-tree
source_root: /media/does-not-matter
target_root: /media/does-not-matter-either
selection_file: examples/selections/music-android-selection-real.yml
syncthing:
  url: http://127.0.0.1:8384
  folder_id: music-android
  device_id: SOME-DEVICE
  api_key_env: SYNCTHING_API_KEY
  timeout_seconds: 5
"""

DEFINITION_YAML_NO_SYNCTHING = """\
app_id: music_android
title: Music Android Selection
view_id: media-tree
source_root: /media/does-not-matter
target_root: /media/does-not-matter-either
selection_file: examples/selections/music-android-selection-real.yml
"""

OBSERVATION = {
    "provider": {"id": "aistack.provider.syncthing"},
    "collected_at": "2026-09-03T18:00:00+00:00",
    "syncthing": {
        "url": "http://127.0.0.1:8384",
        "folder_id": "music-android",
        "device_id": "SOME-DEVICE",
        "reachable": True,
        "unreachable_reason": "",
        "folder": {"state": "idle"},
        "device": {"completion": 100},
    },
}


class FakeSyncthingProvider:
    def __init__(
        self,
        url: str,
        api_key: str,
        folder_id: str,
        device_id: str = "",
        timeout: float = 5.0,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.folder_id = folder_id
        self.device_id = device_id
        self.timeout = timeout

    def collect(self) -> dict[str, Any]:
        return OBSERVATION


@pytest.fixture
def stubbed_provider(monkeypatch) -> list[FakeSyncthingProvider]:
    built: list[FakeSyncthingProvider] = []

    def factory(url, api_key, folder_id, device_id="", timeout=5.0):
        instance = FakeSyncthingProvider(
            url, api_key, folder_id, device_id=device_id, timeout=timeout
        )
        built.append(instance)
        return instance

    monkeypatch.setattr(syncthing_discover, "SyncthingProvider", factory)
    return built


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_it_writes_the_observation_and_keeps_history(stubbed_provider, workspace):
    definition_path = workspace / "music_android.yml"
    definition_path.write_text(DEFINITION_YAML, encoding="utf-8")

    syncthing_discover.main(
        argv=["--definition", str(definition_path)],
        environ={"SYNCTHING_API_KEY": "secret"},
    )

    output_path = (
        workspace / "reports" / "generated" / "music_android-syncthing-observation.json"
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == OBSERVATION

    history_dir = output_path.parent / "history" / "music_android-syncthing-observation"
    history_files = list(history_dir.glob("*.json"))
    assert len(history_files) == 1


def test_it_reads_the_api_key_from_the_named_env_var(stubbed_provider, workspace):
    definition_path = workspace / "music_android.yml"
    definition_path.write_text(DEFINITION_YAML, encoding="utf-8")

    syncthing_discover.main(
        argv=["--definition", str(definition_path)],
        environ={"SYNCTHING_API_KEY": "the-real-key"},
    )

    assert len(stubbed_provider) == 1
    built = stubbed_provider[0]
    assert built.url == "http://127.0.0.1:8384"
    assert built.folder_id == "music-android"
    assert built.device_id == "SOME-DEVICE"
    assert built.api_key == "the-real-key"


def test_a_missing_env_var_reads_as_an_empty_key_not_an_error(
    stubbed_provider, workspace
):
    definition_path = workspace / "music_android.yml"
    definition_path.write_text(DEFINITION_YAML, encoding="utf-8")

    syncthing_discover.main(
        argv=["--definition", str(definition_path)], environ={}
    )

    assert stubbed_provider[0].api_key == ""


def test_it_fails_clearly_when_the_definition_declares_no_syncthing(
    stubbed_provider, workspace, capsys
):
    definition_path = workspace / "music_android.yml"
    definition_path.write_text(DEFINITION_YAML_NO_SYNCTHING, encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        syncthing_discover.main(
            argv=["--definition", str(definition_path)], environ={}
        )

    assert excinfo.value.code == 2
    assert "no Syncthing configuration" in capsys.readouterr().out
    assert stubbed_provider == []


def test_a_second_run_does_not_erase_the_first_observation(
    stubbed_provider, workspace
):
    definition_path = workspace / "music_android.yml"
    definition_path.write_text(DEFINITION_YAML, encoding="utf-8")
    argv = ["--definition", str(definition_path)]
    environ = {"SYNCTHING_API_KEY": "secret"}

    syncthing_discover.main(argv=argv, environ=environ)
    syncthing_discover.main(argv=argv, environ=environ)

    output_path = (
        workspace / "reports" / "generated" / "music_android-syncthing-observation.json"
    )
    history_dir = output_path.parent / "history" / "music_android-syncthing-observation"

    assert len(list(history_dir.glob("*.json"))) == 2
