"""
ADR-0027 § 9, lot 5.8: the web application boots one Kernel and its
screens read through that Kernel's providers, instead of booting another
at every call.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit.web.test_rights import LANGUAGES, LISTENERS

from aistack.kernel.bootstrap import default
from aistack.web.app import create_app


class _Docker:
    def collect(self):
        return {"docker": {"containers": [{"Names": "jellyfin", "State": "running"}]}}


def _app(tmp_path: Path, monkeypatch, **collaborators):
    monkeypatch.setattr("aistack.providers.docker.DockerProvider", _Docker)
    return create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        network_tree=lambda: [],
        syncthing=lambda definition: None,
        **collaborators,
    )


def _no_other_kernel(monkeypatch) -> list[int]:
    booted: list[int] = []

    def boot():
        booted.append(1)
        raise AssertionError("a Kernel was booted for the occasion")

    monkeypatch.setattr(default, "create_kernel", boot)
    return booted


def test_the_default_discovery_reads_through_the_kernel_of_the_app(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, collect_findings=lambda: ((), ""))
    booted = _no_other_kernel(monkeypatch)

    first = app.state.discover_containers()
    second = app.state.discover_containers()

    assert [container.name for container in first] == ["jellyfin"]
    assert len(second) == 1
    assert booted == []


def test_the_default_findings_read_through_the_kernel_of_the_app(tmp_path, monkeypatch):
    monkeypatch.setattr("aistack.providers.docker.DockerProvider", _Docker)
    seen: list[object] = []

    def qualified_findings(providers=None):
        seen.append(providers)
        return (), ""

    monkeypatch.setattr("aistack.web.app.qualified_findings", qualified_findings, raising=True)
    # The default is bound when the app is built, so build it again.
    app = create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        network_tree=lambda: [],
        syncthing=lambda definition: None,
        discover=lambda: (),
    )

    app.state.collect_findings()

    assert seen == [app.state.kernel.registries.providers]


def test_an_injected_collaborator_still_replaces_the_default(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, discover=lambda: (), collect_findings=lambda: ((), "x"))

    assert app.state.discover_containers() == ()
    assert app.state.collect_findings() == ((), "x")
