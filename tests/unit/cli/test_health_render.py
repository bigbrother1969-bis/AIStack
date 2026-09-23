"""
`aistack.cli.health_render` — `PLAN-J7`'s cockpit visuel
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` § 6.4/6.5).

Storage is exercised the same way `test_runtime_diagnose.py` already
exercises it: a real directory `StorageProvider.collect_usage` can
call `shutil.disk_usage` against, no fake. Services is exercised the
same way `test_runtime_diagnose.py` exercises Docker: a `FakeDockerProvider`
standing in for `DockerProvider`, no real daemon. Sauvegarde/PRA is
exercised the same way storage is: a real directory
`BackupProvider.collect_freshness` can walk with `Path.rglob`, no
fake. GPU is exercised the same way Services is: a `FakeGpuProvider`
standing in for `NvidiaGpuProvider`, no real `nvidia-smi` — the sandbox
that runs this suite has no NVIDIA GPU, and a fake makes the result not
depend on whichever machine happens to run it. Tests PRA is exercised
the same way `console`'s own links are: `DEFAULT_PRA_TESTS`
monkeypatched to a real YAML file `load_pra_tests_yaml` reads directly
— there is no live system for a fake Provider to stand in for
(`PraTestReading`'s own docstring: "not a live observation — a
declared record, read as one").

Mirrors `test_the_provider_commands_run.py`'s own end-to-end style for
the "does `main()` write the artifact" test — the same GOV-0002/OS-044
discipline: a command is only proven wired by actually calling it.

The score (`OPS-0008`) is exercised against the real, unpatched
`DEFAULT_HEALTH_SCORE_WEIGHTS` file in most `main()` tests here — it is
not host-scoped the way the four domains are, so there is nothing to
fake; only the "weights file missing" branch is tested with a
monkeypatched path.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.cli import health_render as cli
from aistack.cli import runtime_diagnose
from aistack.contracts.container_health import health_of
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.health_score import DomainWeight, HealthScoreWeights

_DOMAIN_NAMES = {"Stockage", "Services", "Sauvegarde / PRA", "GPU", "Tests PRA"}


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


class FakeGpuProvider:
    """
    Mirrors `FakeDockerProvider` for `NvidiaGpuProvider.collect_readings`
    — no NVIDIA GPU in the sandbox that runs this suite, and a real
    call would make results depend on whichever machine happens to run
    it. Unlike Docker, there is no exception path to fake:
    `collect_readings` is documented never to raise.
    """

    def __init__(self, readings):
        self._readings = readings

    def collect_readings(self):
        return tuple(self._readings)


def gpu_reading(
    temperature_celsius: float = 49.0,
    utilization_percent: float = 1.0,
    memory_used_mib: float = 142.0,
    memory_total_mib: float = 2048.0,
) -> GpuReading:
    return GpuReading(
        name="Quadro P400",
        observed_at=datetime.now(timezone.utc),
        utilization_percent=utilization_percent,
        memory_used_mib=memory_used_mib,
        memory_total_mib=memory_total_mib,
        temperature_celsius=temperature_celsius,
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


def test_all_five_domains_are_always_present(monkeypatch, tmp_path):
    """
    `PLAN-J7` § 1's domain vocabulary, reopened from four to five on
    the owner's own explicit decision, 2026-09-23 (Storage, Services,
    Sauvegarde/PRA, GPU, and now Tests PRA — `PLAN-J11` § 11.9.1's
    third and last named gap, reopened and closed the same day) —
    every build lists all five, whatever their instrumented state,
    never silently fewer (`FDN-0003` Article 12).
    """

    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeDockerProvider(states=[]))

    cockpit = cli.build_cockpit("test-host")

    names = {domain.name for domain in cockpit.domains}
    assert names == _DOMAIN_NAMES


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
# backup_domain — OPS-0004's fourth reference case
# --------------------------------------------------------------------


def backup_thresholds_yaml(path: Path, max_age_days: float) -> str:
    return f"""
hosts:
  - host: test-host
    thresholds:
      - path: {path}
        max_age_days: {max_age_days}
"""


def test_a_missing_backup_file_is_an_alert(monkeypatch, tmp_path):
    backup_dir = tmp_path / "wordpress"
    backup_dir.mkdir()

    path = tmp_path / "backup_thresholds.yml"
    path.write_text(backup_thresholds_yaml(backup_dir, max_age_days=7), encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", path)

    domain = cli.backup_domain("test-host")

    assert domain.instrumented is True
    assert len(domain.findings) == 1
    assert domain.findings[0].qualifications == (
        "OPS-0004/technical-debt",
        "OPS-0004/deployment-misconfiguration",
    )


def test_a_fresh_backup_file_reads_as_clean(monkeypatch, tmp_path):
    backup_dir = tmp_path / "wordpress"
    backup_dir.mkdir()
    (backup_dir / "backup.tar.gz").write_text("data")

    path = tmp_path / "backup_thresholds.yml"
    path.write_text(backup_thresholds_yaml(backup_dir, max_age_days=7), encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", path)

    domain = cli.backup_domain("test-host")

    assert domain.instrumented is True
    assert domain.findings == ()


def test_a_host_with_nothing_declared_for_backups_is_not_instrumented(
    monkeypatch, tmp_path
):
    backup_dir = tmp_path / "wordpress"
    backup_dir.mkdir()

    path = tmp_path / "backup_thresholds.yml"
    path.write_text(backup_thresholds_yaml(backup_dir, max_age_days=7), encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", path)

    domain = cli.backup_domain("a-third-host")

    assert domain.instrumented is False
    assert "a-third-host" in domain.note


def test_a_missing_backup_threshold_definition_is_not_instrumented(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", tmp_path / "absent.yml")

    domain = cli.backup_domain("test-host")

    assert domain.instrumented is False
    assert "no backup-threshold definition at" in domain.note


# --------------------------------------------------------------------
# gpu_domain — OPS-0004's fifth reference case
# --------------------------------------------------------------------


def gpu_thresholds_yaml(celsius: float = 80, percent: float = 90) -> str:
    return f"""
hosts:
  - host: test-host
    thresholds:
      - kind: temperature_celsius
        celsius: {celsius}
      - kind: utilization_percent
        percent: {percent}
      - kind: memory_percent
        percent: {percent}
"""


@pytest.fixture
def gpu_thresholds_file(tmp_path: Path) -> Path:
    path = tmp_path / "gpu_thresholds.yml"
    path.write_text(gpu_thresholds_yaml(), encoding="utf-8")
    return path


def test_a_hot_gpu_reading_is_an_alert(monkeypatch, gpu_thresholds_file):
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", gpu_thresholds_file)
    monkeypatch.setattr(
        cli,
        "NvidiaGpuProvider",
        lambda: FakeGpuProvider([gpu_reading(temperature_celsius=85.0)]),
    )

    domain = cli.gpu_domain("test-host")

    assert domain.instrumented is True
    assert len(domain.findings) == 1
    assert domain.findings[0].qualifications == (
        "OPS-0004/technical-debt",
        "OPS-0004/energy-inefficiency",
        "OPS-0004/sustainability-anomaly",
        "OPS-0004/deployment-misconfiguration",
    )


def test_a_clean_gpu_reading_reads_as_clean(monkeypatch, gpu_thresholds_file):
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", gpu_thresholds_file)
    monkeypatch.setattr(
        cli, "NvidiaGpuProvider", lambda: FakeGpuProvider([gpu_reading()])
    )

    domain = cli.gpu_domain("test-host")

    assert domain.instrumented is True
    assert domain.findings == ()


def test_a_host_with_nothing_declared_for_gpu_is_not_instrumented(
    monkeypatch, gpu_thresholds_file
):
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", gpu_thresholds_file)

    domain = cli.gpu_domain("a-third-host")

    assert domain.instrumented is False
    assert "a-third-host" in domain.note


def test_a_missing_gpu_threshold_definition_is_not_instrumented(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", tmp_path / "absent.yml")

    domain = cli.gpu_domain("test-host")

    assert domain.instrumented is False
    assert "no GPU-threshold definition at" in domain.note


# --------------------------------------------------------------------
# pra_tests_domain — PLAN-J11 § 11.9.1's third and last named gap,
# reopened and closed 2026-09-23. Not host-scoped, unlike every
# domain above — `pra_tests_domain()` takes no hostname.
# --------------------------------------------------------------------


def pra_tests_yaml(
    *,
    max_age_days: float = 90,
    status: str | None = None,
    date: str = "2026-01-01",
    rto_minutes: int | None = None,
) -> str:
    if status is None:
        last_test = "null"
    else:
        rto_line = f"\n      rto_minutes: {rto_minutes}" if rto_minutes is not None else ""
        last_test = f"\n      status: {status}\n      date: \"{date}\"{rto_line}"

    return f"""
max_age_days: {max_age_days}
services:
  - name: nextcloud
    last_test: {last_test}
"""


def test_a_never_tested_service_is_an_alert(monkeypatch, tmp_path):
    path = tmp_path / "pra_tests.yml"
    path.write_text(pra_tests_yaml(status=None), encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", path)

    domain = cli.pra_tests_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1
    assert domain.findings[0].qualifications == (
        "OPS-0004/technical-debt",
        "OPS-0004/sustainability-anomaly",
        "OPS-0004/deployment-misconfiguration",
    )


def test_a_failed_test_is_an_alert(monkeypatch, tmp_path):
    path = tmp_path / "pra_tests.yml"
    path.write_text(
        pra_tests_yaml(status="failed", date="2026-01-01"), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", path)

    domain = cli.pra_tests_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_a_stale_successful_test_is_an_alert(monkeypatch, tmp_path):
    stale_date = (datetime.now(timezone.utc) - timedelta(days=200)).strftime(
        "%Y-%m-%d"
    )
    path = tmp_path / "pra_tests.yml"
    path.write_text(
        pra_tests_yaml(status="success", date=stale_date), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", path)

    domain = cli.pra_tests_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_a_fresh_successful_test_reads_as_clean(monkeypatch, tmp_path):
    fresh_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = tmp_path / "pra_tests.yml"
    path.write_text(
        pra_tests_yaml(status="success", date=fresh_date), encoding="utf-8"
    )
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", path)

    domain = cli.pra_tests_domain()

    assert domain.instrumented is True
    assert domain.findings == ()


def test_a_missing_pra_tests_definition_is_not_instrumented(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")

    domain = cli.pra_tests_domain()

    assert domain.instrumented is False
    assert "no PRA test definition at" in domain.note


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
    # `DEFAULT_PRA_TESTS` is the real, unpatched `OPS-0009` file here —
    # every render, whichever machine runs it, lists Tests PRA too.
    assert "Tests PRA" in document
    assert "non instrumenté" in document
    # `DEFAULT_HEALTH_SCORE_WEIGHTS` is the real, unpatched `OPS-0008`
    # file here — every host, including this sandbox's own, reads a
    # score even with zero domains measured (`OPS-0008` § *Formula*).
    assert "Score de santé" in document


# --------------------------------------------------------------------
# main() — the score (OPS-0008)
# --------------------------------------------------------------------


def test_main_prints_the_score_when_weights_are_available(monkeypatch, tmp_path, workspace, capsys):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")

    cli.main()

    captured = capsys.readouterr()
    assert "score:" in captured.out
    assert "domain(s) measured" in captured.out


def test_main_falls_back_to_the_note_when_weights_are_unavailable(
    monkeypatch, tmp_path, workspace, capsys
):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_HEALTH_SCORE_WEIGHTS", tmp_path / "absent-weights.yml")

    cli.main()

    path = workspace / "reports" / "generated" / "health.html"
    document = path.read_text(encoding="utf-8")
    assert "Score de santé : non calculé" in document
    assert "no health-score weight definition" in document

    captured = capsys.readouterr()
    assert "no health-score weight definition" in captured.out


# --------------------------------------------------------------------
# technical_debt_score — PLAN-J11 § 11.9.1's "dette technique scorée"
# --------------------------------------------------------------------

_ONE_DOMAIN_WEIGHTS = HealthScoreWeights(
    weights=(DomainWeight(domain="Services", points=15),)
)

_NO_SERVICES_WEIGHTS = HealthScoreWeights(
    weights=(DomainWeight(domain="Stockage", points=10),)
)


def test_technical_debt_score_counts_findings_across_every_domain(
    monkeypatch, tmp_path
):
    """
    `OPS-0004/technical-debt` is a qualification any domain's own
    `evaluate_*` may cite (Services, Sauvegarde/PRA and GPU each do) —
    this proves the card is not silently scoped to Services alone.
    """

    backup_dir = tmp_path / "wordpress"
    backup_dir.mkdir()
    backup_path = tmp_path / "backup_thresholds.yml"
    backup_path.write_text(
        f"""
hosts:
  - host: test-host
    thresholds:
      - path: {backup_dir}
        max_age_days: 7
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", backup_path)
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )

    cockpit = cli.build_cockpit("test-host")
    score, note = cli.technical_debt_score(cockpit, _ONE_DOMAIN_WEIGHTS)

    assert note == ""
    assert score is not None
    # One from Services (the restarting container), one from
    # Sauvegarde/PRA (the missing backup) — both cite technical-debt.
    # Tests PRA is deliberately not instrumented here (`DEFAULT_PRA_TESTS`
    # points at nothing) so it contributes none of its own.
    assert len(score.findings) == 2
    assert score.value == 70  # 100 - 2*15


def test_technical_debt_score_ignores_findings_without_the_qualification(
    monkeypatch, tmp_path
):
    """Storage's own findings never cite technical-debt (OPS-0004 § *Second reference incident*)."""

    mount = tmp_path / "volume"
    mount.mkdir()
    storage_path = tmp_path / "storage_thresholds.yml"
    storage_path.write_text(
        f"""
hosts:
  - host: test-host
    thresholds:
      - mount: {mount}
        kind: free_bytes
        free_gb: 999999999
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", storage_path)
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeDockerProvider(states=[]))

    cockpit = cli.build_cockpit("test-host")
    score, note = cli.technical_debt_score(cockpit, _ONE_DOMAIN_WEIGHTS)

    assert note == ""
    assert score is not None
    assert score.findings == ()
    assert score.value == 100


def test_technical_debt_score_reuses_the_services_weight(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )

    cockpit = cli.build_cockpit("test-host")
    weights = HealthScoreWeights(
        weights=(DomainWeight(domain="Services", points=25),)
    )
    score, note = cli.technical_debt_score(cockpit, weights)

    assert note == ""
    assert score.value == 75  # 100 - 1*25


def test_technical_debt_score_is_none_with_a_note_when_weights_are_unavailable():
    cockpit = cli.build_cockpit("test-host")

    score, note = cli.technical_debt_score(cockpit, None)

    assert score is None
    assert "not computed" in note


def test_technical_debt_score_raises_when_no_services_weight_is_declared():
    cockpit = cli.build_cockpit("test-host")

    with pytest.raises(ValueError, match="no weight for domain 'Services'"):
        cli.technical_debt_score(cockpit, _NO_SERVICES_WEIGHTS)


# --------------------------------------------------------------------
# main() — the technical-debt card (PLAN-J11 § 11.9.1)
# --------------------------------------------------------------------


def test_main_writes_the_technical_debt_card(monkeypatch, tmp_path, workspace):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")

    cli.main()

    path = workspace / "reports" / "generated" / "health.html"
    document = path.read_text(encoding="utf-8")

    assert "Dette technique" in document


def test_main_prints_the_technical_debt_score(monkeypatch, tmp_path, workspace, capsys):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")

    cli.main()

    captured = capsys.readouterr()
    assert "Technical-debt score:" in captured.out


def test_main_falls_back_to_the_note_for_technical_debt_when_weights_are_unavailable(
    monkeypatch, tmp_path, workspace, capsys
):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_HEALTH_SCORE_WEIGHTS", tmp_path / "absent-weights.yml")

    cli.main()

    path = workspace / "reports" / "generated" / "health.html"
    document = path.read_text(encoding="utf-8")
    assert "Dette technique : non calculée" in document

    captured = capsys.readouterr()
    assert "Technical-debt score: no health-score weight definition" in captured.out


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


def test_the_default_backup_thresholds_path_matches_runtime_diagnoses():
    """
    Mirrors `test_the_default_storage_thresholds_path_matches_runtime_diagnoses`
    for `OPS-0006`'s own file.
    """

    assert cli.DEFAULT_BACKUP_THRESHOLDS == runtime_diagnose.DEFAULT_BACKUP_THRESHOLDS
    assert cli.DEFAULT_BACKUP_THRESHOLDS.exists()


def test_the_default_gpu_thresholds_path_matches_runtime_diagnoses():
    """
    Mirrors `test_the_default_backup_thresholds_path_matches_runtime_diagnoses`
    for `OPS-0007`'s own file.
    """

    assert cli.DEFAULT_GPU_THRESHOLDS == runtime_diagnose.DEFAULT_GPU_THRESHOLDS
    assert cli.DEFAULT_GPU_THRESHOLDS.exists()


def test_the_default_health_score_weights_definition_exists():
    """
    Unlike the three `DEFAULT_*_THRESHOLDS` above, `OPS-0008` has no
    sibling in `runtime_diagnose.py` to drift against — a health score
    is only ever computed here, in `health_render.py`. This just
    confirms the declared path resolves to a real, readable file.
    """

    assert cli.DEFAULT_HEALTH_SCORE_WEIGHTS.exists()


def test_the_default_pra_tests_definition_exists():
    """
    Mirrors `test_the_default_health_score_weights_definition_exists`:
    `OPS-0009` has no sibling in `runtime_diagnose.py` either — a
    restore test is hand-maintained, never collected by a live
    Provider that runtime diagnose could also reach.
    """

    assert cli.DEFAULT_PRA_TESTS.exists()
