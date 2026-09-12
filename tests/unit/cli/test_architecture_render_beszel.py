"""
`aistack.cli.architecture_render` — the Beszel wiring added
2026-09-12 (`claude/PLAN-J11-CONSOLE-2026-09-11.md` §10, last
bullet).

Driven directly against `main(environ=...)`, the same way
`test_jellyfin_discover.py` drives `jellyfin_discover.main` — a
stubbed `BeszelProvider` in place of the real hub, so no test in
this file ever makes a real network call to
`https://beszel.persiaut-family.fr`. Docker and Compose are stubbed
the same way `test_the_provider_commands_run.py` already stubs them,
since `architecture_render.main()` reaches both first.

What is under test here is the wiring `architecture_render.py` itself
adds: the real topology's `beszel:` block names two env var names,
this command resolves them through the `environ` it was given (real
`os.environ` by default, injectable for tests), hands the resolved
*values* to `BeszelProvider` (never the names — GOV-P-001, "the
key/credential is a value, never a lookup"), writes the raw
observation as a governed artifact with History, and threads the
built readings through to the rendered page. The non-fatal
degradation path (unreachable/unconfigured Beszel still yields a
page, just with no "État en direct" section) is already covered at
`render_html`'s own level (`test_html.py`); this file is about the
CLI reaching that point correctly, not re-proving the renderer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import architecture_render


OBSERVED_AT = "2026-09-12T12:00:00+00:00"


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


class FakeBeszelProvider:
    """
    Records what it was constructed with and returns a canned
    observation — the same shape `BeszelProvider.collect()` itself
    produces, so `build_beszel_readings` downstream sees a realistic
    payload.
    """

    instances: list["FakeBeszelProvider"] = []
    next_observation: dict[str, Any]

    def __init__(self, url: str, email: str, password: str, timeout: float = 5.0) -> None:
        self.url = url
        self.email = email
        self.password = password
        self.timeout = timeout
        FakeBeszelProvider.instances.append(self)

    def collect(self) -> dict:
        return FakeBeszelProvider.next_observation


_DEFAULT_OBSERVATION: dict[str, Any] = {
    "provider": {"id": "aistack.provider.beszel", "name": "Beszel Provider"},
    "collected_at": OBSERVED_AT,
    "beszel": {
        "url": "https://beszel.persiaut-family.fr",
        "reachable": False,
        "unreachable_reason": "no credentials were provided, so Beszel was not asked",
        "systems": [],
    },
}


@pytest.fixture(autouse=True)
def reset_fake_beszel():
    FakeBeszelProvider.instances = []
    FakeBeszelProvider.next_observation = dict(_DEFAULT_OBSERVATION)
    yield
    FakeBeszelProvider.instances = []
    FakeBeszelProvider.next_observation = dict(_DEFAULT_OBSERVATION)


@pytest.fixture
def stubbed_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.DockerProvider", FakeDockerProvider
    )
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.ComposeProvider", FakeComposeProvider
    )
    monkeypatch.setattr(architecture_render, "BeszelProvider", FakeBeszelProvider)


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _observation_with_systems(systems: list[dict]) -> dict:
    return {
        "provider": {"id": "aistack.provider.beszel", "name": "Beszel Provider"},
        "collected_at": OBSERVED_AT,
        "beszel": {
            "url": "https://beszel.persiaut-family.fr",
            "reachable": True,
            "unreachable_reason": "",
            "systems": systems,
        },
    }


# --------------------------------------------------------------------
# Env var names in, resolved values out — never the other way round
# --------------------------------------------------------------------


def test_the_real_topologys_env_var_names_are_resolved_through_environ(
    stubbed_providers, workspace
):
    architecture_render.main(
        environ={"BESZEL_EMAIL": "aistack-readonly@persiaut-family.fr", "BESZEL_PASSWORD": "s3cr3t"}
    )

    assert len(FakeBeszelProvider.instances) == 1
    built = FakeBeszelProvider.instances[0]
    assert built.url == "https://beszel.persiaut-family.fr"
    assert built.email == "aistack-readonly@persiaut-family.fr"
    assert built.password == "s3cr3t"


def test_missing_env_vars_resolve_to_empty_strings_not_a_raise(
    stubbed_providers, workspace
):
    architecture_render.main(environ={})

    assert len(FakeBeszelProvider.instances) == 1
    built = FakeBeszelProvider.instances[0]
    assert built.email == ""
    assert built.password == ""


# --------------------------------------------------------------------
# The observation is written as a governed artifact with History
# --------------------------------------------------------------------


def test_the_beszel_observation_is_written_with_history(stubbed_providers, workspace):
    architecture_render.main(environ={})

    output_path = workspace / "reports" / "generated" / "beszel-observation.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        FakeBeszelProvider.next_observation
    )

    history_dir = output_path.parent / "history" / "beszel-observation"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_a_second_run_does_not_erase_the_first_beszel_observation(
    stubbed_providers, workspace
):
    architecture_render.main(environ={})
    architecture_render.main(environ={})

    history_dir = (
        workspace / "reports" / "generated" / "history" / "beszel-observation"
    )
    assert len(list(history_dir.glob("*.json"))) == 2


# --------------------------------------------------------------------
# Readings reach the rendered page
# --------------------------------------------------------------------


def test_a_reachable_hub_with_systems_threads_readings_into_the_page(
    stubbed_providers, workspace
):
    FakeBeszelProvider.next_observation = _observation_with_systems(
        [
            {
                "name": "Gigabyte",
                "host": "192.168.1.10",
                "status": "up",
                "info": {"cpu": 17.42, "mp": 67.74},
            }
        ]
    )

    architecture_render.main(environ={})

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")

    assert '<section class="beszel-index">' in document
    assert "<h4>Gigabyte</h4>" in document
    assert '<span class="beszel-status beszel-status-up">up</span>' in document
    assert "<dt>CPU</dt><dd>17.4 %</dd>" in document


def test_an_unreachable_hub_renders_a_page_with_no_beszel_section(
    stubbed_providers, workspace
):
    """
    The non-fatal path: `FakeBeszelProvider.next_observation`
    defaults to `reachable: False, systems: []` — the run must still
    produce a complete `architecture.html`, just without an "État en
    direct" section, exactly as `render_html` behaves when given an
    empty tuple of readings.
    """

    architecture_render.main(environ={})

    output_path = workspace / "reports" / "generated" / "architecture.html"
    document = output_path.read_text(encoding="utf-8")

    assert document.startswith("<!doctype html>")
    assert '<section class="beszel-index">' not in document


# --------------------------------------------------------------------
# No `beszel:` block at all — BeszelProvider is never even built
# --------------------------------------------------------------------


def test_a_topology_with_no_beszel_block_never_constructs_the_provider(
    stubbed_providers, workspace, monkeypatch
):
    topology_path = workspace / "infrastructure_topology.yml"
    topology_path.write_text("external_nodes: []\n", encoding="utf-8")
    monkeypatch.setattr(architecture_render, "DEFAULT_TOPOLOGY", topology_path)

    architecture_render.main(environ={"BESZEL_EMAIL": "x", "BESZEL_PASSWORD": "y"})

    assert FakeBeszelProvider.instances == []
    assert not (
        workspace / "reports" / "generated" / "beszel-observation.json"
    ).exists()

    document = (
        workspace / "reports" / "generated" / "architecture.html"
    ).read_text(encoding="utf-8")
    assert '<section class="beszel-index">' not in document
