"""
`aistack.cli.jellyfin_discover` — the on-demand command chosen
2026-09-03 to extend Observation History to Jellyfin, deliberately
separate from the CPU monitor's 5-second poll (which would produce
tens of thousands of near-duplicate history files a day, not what
"keep everything, indefinitely" was decided for).

Driven directly against `main()`, the way `test_the_provider_
commands_run.py` drives the four provider CLIs — a stubbed
`JellyfinProvider` in place of the real daemon, and a real
resource-priority definition file (not read from the repository's
own) so the test does not depend on GIGABYTE-only configuration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import jellyfin_discover
from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.yaml import save_resource_priority_yaml


OBSERVATION = {
    "provider": {"id": "aistack.provider.jellyfin"},
    "collected_at": "2026-09-03T18:00:00+00:00",
    "jellyfin": {
        "url": "http://127.0.0.1:8096",
        "reachable": True,
        "unreachable_reason": "",
        "sessions": [{"NowPlayingItem": {"Name": "Example"}}],
    },
}


class FakeJellyfinProvider:
    """A Jellyfin provider that observes without a real daemon."""

    def __init__(self, url: str, api_key: str, timeout: float = 5.0) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout = timeout

    def collect(self) -> dict[str, Any]:
        return OBSERVATION


@pytest.fixture
def stubbed_provider(monkeypatch) -> list[FakeJellyfinProvider]:
    """
    Captures every `JellyfinProvider(...)` construction, so a test
    can assert what was actually passed in — the URL and the API
    key read from the environment variable the definition names.
    """

    built: list[FakeJellyfinProvider] = []

    def factory(url: str, api_key: str, timeout: float = 5.0):
        instance = FakeJellyfinProvider(url, api_key, timeout=timeout)
        built.append(instance)
        return instance

    monkeypatch.setattr(jellyfin_discover, "JellyfinProvider", factory)
    return built


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    """The command writes under a relative `reports/generated/`."""

    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_definition(
    path: Path,
    *,
    detector: JellyfinDetectorDefinition | CpuThresholdDetectorDefinition,
) -> Path:
    definition = ResourcePriorityDefinition(
        priority=(
            PriorityAppDefinition(
                container="jellyfin",
                normal_cpus=3.0,
                boosted_cpus=4.0,
                detector=detector,
            ),
        ),
        background=BackgroundPriorityDefinition(default_throttled_cpus=0.1),
        unlimited_cpus=4.0,
        grace_seconds=60.0,
    )
    save_resource_priority_yaml(definition, path)
    return path


def test_it_writes_the_observation_and_keeps_history(
    stubbed_provider, workspace, monkeypatch
):
    definition_path = _write_definition(
        workspace / "resource_priority.yml",
        detector=JellyfinDetectorDefinition(
            url="http://127.0.0.1:8096",
            api_key_env="JELLYFIN_API_KEY",
            timeout_seconds=5.0,
        ),
    )

    jellyfin_discover.main(
        argv=["--definition", str(definition_path)],
        environ={"JELLYFIN_API_KEY": "secret"},
    )

    output_path = workspace / "reports" / "generated" / "jellyfin-observation.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == OBSERVATION

    history_dir = output_path.parent / "history" / "jellyfin-observation"
    history_files = list(history_dir.glob("*.json"))
    assert len(history_files) == 1
    assert history_files[0].read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )


def test_it_reads_the_url_and_api_key_from_the_named_env_var(
    stubbed_provider, workspace
):
    definition_path = _write_definition(
        workspace / "resource_priority.yml",
        detector=JellyfinDetectorDefinition(
            url="http://127.0.0.1:8096",
            api_key_env="JELLYFIN_API_KEY",
            timeout_seconds=7.5,
        ),
    )

    jellyfin_discover.main(
        argv=["--definition", str(definition_path)],
        environ={"JELLYFIN_API_KEY": "the-real-key"},
    )

    assert len(stubbed_provider) == 1
    built = stubbed_provider[0]
    assert built.url == "http://127.0.0.1:8096"
    assert built.api_key == "the-real-key"
    assert built.timeout == 7.5


def test_a_missing_env_var_reads_as_an_empty_key_not_an_error(
    stubbed_provider, workspace
):
    """
    GOV-P-001 handling, same as `build_detector`'s own factory: the
    definition names where the key lives, and an unset variable is
    a state the provider itself reports (`unreachable_reason`), not
    a reason for this command to raise before ever asking.
    """

    definition_path = _write_definition(
        workspace / "resource_priority.yml",
        detector=JellyfinDetectorDefinition(
            url="http://127.0.0.1:8096",
            api_key_env="JELLYFIN_API_KEY",
            timeout_seconds=5.0,
        ),
    )

    jellyfin_discover.main(
        argv=["--definition", str(definition_path)], environ={}
    )

    assert stubbed_provider[0].api_key == ""


def test_it_fails_clearly_when_no_priority_app_declares_jellyfin(
    stubbed_provider, workspace, capsys
):
    definition_path = _write_definition(
        workspace / "resource_priority.yml",
        detector=CpuThresholdDetectorDefinition(
            threshold_percent=50.0, sustained_seconds=15.0
        ),
    )

    with pytest.raises(SystemExit) as excinfo:
        jellyfin_discover.main(
            argv=["--definition", str(definition_path)], environ={}
        )

    assert excinfo.value.code == 2
    assert "Jellyfin" in capsys.readouterr().out
    assert stubbed_provider == []


def test_a_second_run_does_not_erase_the_first_observation(
    stubbed_provider, workspace
):
    definition_path = _write_definition(
        workspace / "resource_priority.yml",
        detector=JellyfinDetectorDefinition(
            url="http://127.0.0.1:8096",
            api_key_env="JELLYFIN_API_KEY",
            timeout_seconds=5.0,
        ),
    )
    argv = ["--definition", str(definition_path)]
    environ = {"JELLYFIN_API_KEY": "secret"}

    jellyfin_discover.main(argv=argv, environ=environ)
    jellyfin_discover.main(argv=argv, environ=environ)

    output_path = workspace / "reports" / "generated" / "jellyfin-observation.json"
    history_dir = output_path.parent / "history" / "jellyfin-observation"

    assert len(list(history_dir.glob("*.json"))) == 2
