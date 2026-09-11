"""
`aistack.cli.health_render` — `PLAN-J7`'s cockpit visuel
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` § 6.4/6.5).

Storage is exercised the same way `test_runtime_diagnose.py` already
exercises it: a real directory `StorageProvider.collect_usage` can
call `shutil.disk_usage` against, no fake. Services is exercised the
same way `test_runtime_diagnose.py` exercises Docker: a `FakeDockerProvider`
standing in for `DockerProvider`, no real daemon. The two remaining
not-yet-named domains (Sauvegarde/PRA, GPU) are asserted present and
explicitly not-instrumented on every run — `FDN-0003` Article 12 says
their absence is what must be shown, not silence.

Mirrors `test_the_provider_commands_run.py`'s own end-to-end style for
the "does `main()` write the artifact" test — the same GOV-0002/OS-044
discipline: a command is only proven wired by actually calling it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.cli import health_render as cli
from aistack.cli import runtime_diagnose
from aistack.contracts.container_health import health_of
from aistack.contracts.container_state_reading import ContainerStateReading


class FakeDockerProvider:
    """
    Mirrors `test_runtime_diagnose.py`'s own `FakeProvider` for the
    one method this module calls: no Docker daemon in the sandbox
    that runs this suite, and a real one would make results depend
    on this machine — exactly the reasoning that file already gives.
    """

    def __init__(self, states):
        self._states = states

    def collect_container_states(self):
        if isinstance(self._states, Exception):
            raise self._states

        return tuple(
            ContainerStateReading(
                container=entry["Names"],
                state=entry.get("State") or "unknown",
                health=health_of(entry.get("Status")),
            )
            for entry in (self._states or ())
        )


@pytest.fixture
def storage_mount(tmp_path: Path) -> Path:
    mount = tmp_path / "volume"
    mount.mkdir()
    return mount


def storage_thresholds_yaml(mount: Path, free_gb: float) -> str:
    return f"""
hosts:
  - host: test-host
    thresholds:
      - mount: {mount}
        kind: free_bytes
        free_gb: {free_gb}
"""


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------
# build_cockpit — the domains, without going through main()/HTML
# --------------------------------------------------------------------


def test_a_mount_below_its_threshold_is_an_alert(monkeypatch, tmp_path, storage_mount):
    path = tmp_path / "storage_thresholds.yml"
    path.write_text(
        storage_thresholds_yaml(storage_mount, free_gb=999_999_999),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", path)

    cockpit = cli.build_cockpit("test-host")

    storage = next(d for d in cockpit.domains if d.name == "Stockage")
    assert storage.instrumented is True
    assert len(storage.findings) == 1
    assert storage.findings[0].qualifications == (
        "OPS-0004/deployment-misconfiguration",
    )


def test_a_mount_above_its_threshold_reads_as_clean(monkeypatch, tmp_path, storage_mount):
    path = tmp_path / "storage_thresholds.yml"
    path.write_text(storage_thresholds_yaml(storage_mount, free_gb=0), encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", path)

    cockpit = cli.build_cockpit("test-host")

    storage = next(d for d in cockpit.domains if d.name == "Stockage")
    assert storage.instrumented is True
    assert storage.findings == ()


def test_a_host_with_nothing_declared_is_not_instrumented(
    monkeypatch, tmp_path, storage_mount
):
    path = tmp_path / "storage_thresholds.yml"
    path.write_text(
        storage_thresholds_yaml(storage_mount, free_gb=999_999_999),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", path)

    cockpit = cli.build_cockpit("a-third-host")

    storage = next(d for d in cockpit.domains if d.name == "Stockage")
    assert storage.instrumented is False
    assert "a-third-host" in storage.note


def test_a_missing_storage_threshold_definition_is_not_instrumented(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")

    cockpit = cli.build_cockpit("test-host")

    storage = next(d for d in cockpit.domains if d.name == "Stockage")
    assert storage.instrumented is False
    assert "no storage-threshold definition at" in storage.note


def test_the_two_undeclared_domains_are_always_present_and_not_instrumented(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeDockerProvider(states=[]))

    cockpit = cli.build_cockpit("test-host")

    names = {domain.name: domain for domain in cockpit.domains}
    assert set(names) == {"Stockage", "Services", "Sauvegarde / PRA", "GPU"}

    for name in ("Sauvegarde / PRA", "GPU"):
        assert names[name].instrumented is False
        assert names[name].note == cli.NOT_YET_INSTRUMENTED


# --------------------------------------------------------------------
# services_domain — OPS-0004's third reference incident
# --------------------------------------------------------------------


def test_a_restarting_container_is_an_alert(monkeypatch):
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )

    domain = cli.services_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1
    assert domain.findings[0].qualifications == (
        "OPS-0004/technical-debt",
        "OPS-0004/sustainability-anomaly",
        "OPS-0004/deployment-misconfiguration",
    )


def test_a_clean_docker_host_reads_as_clean(monkeypatch):
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(
            states=[
                {
                    "Names": "gluetun",
                    "State": "running",
                    "Status": "Up 2 hours (healthy)",
                }
            ]
        ),
    )

    domain = cli.services_domain()

    assert domain.instrumented is True
    assert domain.findings == ()


def test_docker_not_reachable_is_not_instrumented(monkeypatch):
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=OSError("docker not found")),
    )

    domain = cli.services_domain()

    assert domain.instrumented is False
    assert "container states could not be collected" in domain.note


# --------------------------------------------------------------------
# main() — end to end
# --------------------------------------------------------------------


def test_main_writes_the_health_html_artifact(monkeypatch, tmp_path, workspace):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")

    cli.main()

    path = workspace / "reports" / "generated" / "health.html"
    assert path.exists()

    document = path.read_text(encoding="utf-8")
    assert document.startswith("<!doctype html>")
    assert "Cockpit Santé" in document
    assert "GPU" in document
    assert "non instrumenté" in document


# --------------------------------------------------------------------
# Both CLIs read the same governed file — a real drift-guard
# --------------------------------------------------------------------


def test_the_default_storage_thresholds_path_matches_runtime_diagnoses():
    """
    `health_render.py` declares its own `DEFAULT_STORAGE_THRESHOLDS`
    rather than importing `runtime_diagnose`'s (no CLI in this
    package imports another) — this is the check that the duplication
    stayed in sync: both must resolve to the exact same file on disk.
    """

    assert cli.DEFAULT_STORAGE_THRESHOLDS == runtime_diagnose.DEFAULT_STORAGE_THRESHOLDS
    assert cli.DEFAULT_STORAGE_THRESHOLDS.exists()
