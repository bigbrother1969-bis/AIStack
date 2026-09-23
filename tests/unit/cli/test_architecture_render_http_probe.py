"""
`aistack.cli.architecture_render` — the HTTP probe wiring added
2026-09-23 (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §11.9.1, first of
the three gaps named 2026-09-13).

Driven directly against `main(environ=...)`, the same way
`test_architecture_render_beszel.py` drives it — a stubbed
`HttpProbeProvider` in place of real network calls, and a stubbed
`DEFAULT_CMDB_TARGETS` path in place of the real, shipped target list,
so no test in this file ever probes a real `*.persiaut-family.fr`
endpoint. Docker and Compose are stubbed the same way
`test_the_provider_commands_run.py` already stubs them, since
`architecture_render.main()` reaches both first.

What is under test here is the wiring `architecture_render.py` itself
adds: the real target list is loaded, handed to `HttpProbeProvider`,
the raw observation is written as a governed artifact with History,
and the built readings are threaded through to the rendered page. The
non-fatal degradation path (no targets configured still yields a
page, just with no "CMDB temps réel" section) is already covered at
`render_html`'s own level (`test_html.py`); this file is about the CLI
reaching that point correctly, not re-proving the renderer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import architecture_render


OBSERVED_AT = "2026-09-23T12:00:00+00:00"


class FakeDockerProvider:
    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.docker"},
            "collected_at": OBSERVED_AT,
            "docker": {"containers": [], "images": [], "networks": [], "volumes": []},
        }


class FakeComposeProvider:
    def collect(self) -> dict:
        return {
            "provider": {"id": "aistack.provider.compose"},
            "collected_at": OBSERVED_AT,
            "compose": {"projects": []},
        }


class FakeHttpProbeProvider:
    """
    Records what it was constructed with and returns a canned
    observation — the same shape `HttpProbeProvider.collect()` itself
    produces, so `build_http_probe_readings` downstream sees a
    realistic payload.
    """

    instances: list["FakeHttpProbeProvider"] = []
    next_observation: dict[str, Any]

    def __init__(self, targets: tuple, timeout: float = 5.0) -> None:
        self.targets = targets
        self.timeout = timeout
        FakeHttpProbeProvider.instances.append(self)

    def collect(self) -> dict:
        return FakeHttpProbeProvider.next_observation


def _default_observation() -> dict[str, Any]:
    return {
        "provider": {"id": "aistack.provider.http_probe", "name": "HTTP Probe Provider"},
        "collected_at": OBSERVED_AT,
        "http_probe": {"targets": []},
    }


@pytest.fixture(autouse=True)
def reset_fake_http_probe():
    FakeHttpProbeProvider.instances = []
    FakeHttpProbeProvider.next_observation = _default_observation()
    yield
    FakeHttpProbeProvider.instances = []
    FakeHttpProbeProvider.next_observation = _default_observation()


@pytest.fixture
def stubbed_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.DockerProvider", FakeDockerProvider
    )
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.ComposeProvider", FakeComposeProvider
    )
    monkeypatch.setattr(architecture_render, "HttpProbeProvider", FakeHttpProbeProvider)


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def one_target(workspace, monkeypatch) -> Path:
    targets_path = workspace / "cmdb_probe_targets.yml"
    targets_path.write_text(
        "targets:\n  - name: Gitea\n    url: https://gitea.persiaut-family.fr\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(architecture_render, "DEFAULT_CMDB_TARGETS", targets_path)
    return targets_path


def _observation_with_targets(targets: list[dict]) -> dict:
    return {
        "provider": {"id": "aistack.provider.http_probe", "name": "HTTP Probe Provider"},
        "collected_at": OBSERVED_AT,
        "http_probe": {"targets": targets},
    }


# --------------------------------------------------------------------
# The loaded target list reaches the provider, as (name, url) pairs
# --------------------------------------------------------------------


def test_the_real_targets_are_resolved_into_name_url_pairs(
    stubbed_providers, workspace, one_target
):
    architecture_render.main(environ={})

    assert len(FakeHttpProbeProvider.instances) == 1
    built = FakeHttpProbeProvider.instances[0]
    assert built.targets == (("Gitea", "https://gitea.persiaut-family.fr"),)


# --------------------------------------------------------------------
# The observation is written as a governed artifact with History
# --------------------------------------------------------------------


def test_the_http_probe_observation_is_written_with_history(
    stubbed_providers, workspace, one_target
):
    architecture_render.main(environ={})

    output_path = workspace / "reports" / "generated" / "http-probe-observation.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        FakeHttpProbeProvider.next_observation
    )

    history_dir = output_path.parent / "history" / "http-probe-observation"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_a_second_run_does_not_erase_the_first_http_probe_observation(
    stubbed_providers, workspace, one_target
):
    architecture_render.main(environ={})
    architecture_render.main(environ={})

    history_dir = (
        workspace / "reports" / "generated" / "history" / "http-probe-observation"
    )
    assert len(list(history_dir.glob("*.json"))) == 2


# --------------------------------------------------------------------
# Readings reach the rendered page
# --------------------------------------------------------------------


def test_reachable_targets_thread_readings_into_the_page(
    stubbed_providers, workspace, one_target
):
    FakeHttpProbeProvider.next_observation = _observation_with_targets(
        [
            {
                "name": "Gitea",
                "url": "https://gitea.persiaut-family.fr",
                "reachable": True,
                "status_code": 200,
                "unreachable_reason": "",
            }
        ]
    )

    architecture_render.main(environ={})

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")

    assert '<section class="cmdb-index">' in document
    assert "<h4>Gitea</h4>" in document
    assert '<span class="cmdb-status cmdb-status-ok">200</span>' in document


def test_an_unreachable_target_renders_the_injoignable_state(
    stubbed_providers, workspace, one_target
):
    FakeHttpProbeProvider.next_observation = _observation_with_targets(
        [
            {
                "name": "Gitea",
                "url": "https://gitea.persiaut-family.fr",
                "reachable": False,
                "status_code": None,
                "unreachable_reason": "https://gitea.persiaut-family.fr could not be reached: timed out",
            }
        ]
    )

    architecture_render.main(environ={})

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")

    assert (
        '<span class="cmdb-status cmdb-status-unreachable">Injoignable</span>'
        in document
    )


# --------------------------------------------------------------------
# No targets at all — HttpProbeProvider is never even constructed
# --------------------------------------------------------------------


def test_an_empty_target_list_never_constructs_the_provider(
    stubbed_providers, workspace, monkeypatch
):
    targets_path = workspace / "cmdb_probe_targets.yml"
    targets_path.write_text("targets: []\n", encoding="utf-8")
    monkeypatch.setattr(architecture_render, "DEFAULT_CMDB_TARGETS", targets_path)

    architecture_render.main(environ={})

    assert FakeHttpProbeProvider.instances == []
    assert not (
        workspace / "reports" / "generated" / "http-probe-observation.json"
    ).exists()

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")
    assert '<section class="cmdb-index">' not in document
