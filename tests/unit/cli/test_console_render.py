"""
`aistack.cli.console_render` — `PLAN-J11`'s console
(`claude/PLAN-J11-CONSOLE-2026-09-11.md` § 2/§ 4).

Mirrors `test_health_render.py`'s own end-to-end style for the "does
`main()` write the artifact" test — the same GOV-0002/OS-044
discipline: a command is only proven wired by actually calling it.
This module additionally exercises the one piece no other `cli/*`
command has: `PUBLIC_DIR`'s relative symlinks, the fix for the gap
`PLAN-J11` § 4 found — nothing before this command ever served
`reports/generated/` over HTTP at all.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from aistack.cli import console_render as cli
from aistack.cli import health_render
from aistack.contracts.container_health import health_of
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.health_score import DomainWeight, HealthScoreWeights


class FakeDockerProvider:
    """Mirrors `test_health_render.py`'s own fake for the same reason."""

    def __init__(self, states):
        self._states = states

    def collect_container_states(self):
        return tuple(
            ContainerStateReading(
                container=entry["Names"],
                state=entry.get("State") or "unknown",
                health=health_of(entry.get("Status")),
            )
            for entry in (self._states or ())
        )

    def collect(self):
        """Mirrors `test_health_render.py`'s own fake for the same reason."""

        return {
            "provider": {"id": "fake", "name": "Fake Docker Provider"},
            "collected_at": "2026-09-30T00:00:00+00:00",
            "docker": {
                "containers": list(self._states or ()),
                "images": [],
                "networks": [],
                "volumes": [],
            },
        }


class FakeGpuProvider:
    """Mirrors `test_health_render.py`'s own fake for the same reason."""

    def __init__(self, readings):
        self._readings = readings

    def collect_readings(self):
        return tuple(self._readings)


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------
# main() — end to end
# --------------------------------------------------------------------


def test_main_writes_the_console_html_artifact(workspace):
    cli.main()

    path = workspace / "reports" / "generated" / "console.html"
    assert path.exists()

    document = path.read_text(encoding="utf-8")
    assert document.startswith("<!doctype html>")
    assert "Selection UI" in document
    assert "Cockpit Santé" in document
    # PLAN-J11 § 11.9 — the health cartouche, built from a real
    # HealthCockpit against this sandbox's own hostname: whichever
    # host runs this suite, `main()` still writes all six domains.
    assert "État de santé du homelab" in document
    # PLAN-J11 § 11.9.1's third and last named gap ("tests PRA"),
    # reopened and closed 2026-09-23 — `DEFAULT_PRA_TESTS` is the
    # real, unpatched `OPS-0009` file here too.
    assert "Tests PRA" in document
    # PLAN-J11 § 11.9.1 — the "Dette technique" card, added 2026-09-23.
    assert "Dette technique" in document


def test_main_writes_one_console_per_declared_language(workspace):
    """
    ADR-0010 § 5 (2026-09-27): the reference language keeps
    `console.html` and its history stream; every other declared
    language adds `console.<code>.html` beside it.
    """

    cli.main()

    generated_dir = workspace / "reports" / "generated"
    english = (generated_dir / "console.en.html").read_text(encoding="utf-8")
    french = (generated_dir / "console.html").read_text(encoding="utf-8")

    assert '<html lang="fr">' in french
    assert '<html lang="en">' in english
    assert "Homelab health" in english
    assert "Health cockpit" in english
    assert "http://GIGABYTE:8187/selection/?lang=en" in english
    assert "http://GIGABYTE:8187/selection/?lang=fr" in french
    assert (generated_dir / "history" / "console").is_dir()
    assert (generated_dir / "history" / "console.en").is_dir()


def test_main_prints_a_confirmation_line(workspace, capsys):
    cli.main()

    captured = capsys.readouterr()
    assert "Console written to" in captured.out
    assert "7 link(s)" in captured.out
    assert "served from" in captured.out


def test_main_creates_the_public_directory_with_an_index(workspace):
    cli.main()

    index = workspace / "reports" / "generated" / "public" / "index.html"
    assert index.exists()
    assert "console.html" in index.read_text(encoding="utf-8")


def test_main_symlinks_the_three_served_artifacts_into_public(workspace):
    cli.main()

    public_dir = workspace / "reports" / "generated" / "public"

    for name, target in (
        ("console.html", "../console.html"),
        ("architecture.html", "../architecture.html"),
        ("health.html", "../health.html"),
    ):
        link = public_dir / name
        assert link.is_symlink()
        assert str(link.readlink()) == target


def test_the_console_html_is_reachable_through_its_own_symlink(workspace):
    cli.main()

    public_dir = workspace / "reports" / "generated" / "public"

    assert (public_dir / "console.html").read_text(encoding="utf-8") == (
        workspace / "reports" / "generated" / "console.html"
    ).read_text(encoding="utf-8")


def test_running_main_twice_is_idempotent(workspace):
    cli.main()
    cli.main()

    public_dir = workspace / "reports" / "generated" / "public"
    assert (public_dir / "console.html").is_symlink()


def test_history_lives_beside_the_generated_file_not_inside_public(workspace):
    """
    `PLAN-J11` § 4: `PUBLIC_DIR` exposes exactly three pages, never
    `write_artifact_with_history`'s own `history/` subdirectory — that
    subdirectory is created beside `console.html`
    (`reports/generated/history/console/`), never inside
    `reports/generated/public/`, so a server rooted at `PUBLIC_DIR`
    never reaches it.
    """

    cli.main()

    generated_dir = workspace / "reports" / "generated"
    public_dir = generated_dir / "public"

    assert (generated_dir / "history" / "console").is_dir()
    assert not (public_dir / "history").exists()


# --------------------------------------------------------------------
# _ensure_public_symlink — the one piece of plumbing this command
# owns outright
# --------------------------------------------------------------------


def test_ensure_public_symlink_creates_a_new_link(tmp_path: Path):
    link_path = tmp_path / "architecture.html"

    cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert link_path.is_symlink()
    assert str(link_path.readlink()) == "../architecture.html"


def test_ensure_public_symlink_leaves_a_matching_link_alone(tmp_path: Path):
    link_path = tmp_path / "architecture.html"
    link_path.symlink_to(Path("../architecture.html"))
    inode_before = link_path.lstat().st_ino

    cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert link_path.lstat().st_ino == inode_before


def test_ensure_public_symlink_repairs_a_link_pointing_elsewhere(tmp_path: Path):
    link_path = tmp_path / "architecture.html"
    link_path.symlink_to(Path("../somewhere-else.html"))

    cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert str(link_path.readlink()) == "../architecture.html"


def test_ensure_public_symlink_refuses_to_clobber_a_real_file(tmp_path: Path):
    link_path = tmp_path / "architecture.html"
    link_path.write_text("not managed by this command", encoding="utf-8")

    with pytest.raises(ValueError, match="not a symlink this command manages"):
        cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert link_path.read_text(encoding="utf-8") == "not managed by this command"


# --------------------------------------------------------------------
# DEFAULT_CONSOLE_LINKS — the real, governed file
# --------------------------------------------------------------------


def test_the_default_console_links_definition_exists():
    assert cli.DEFAULT_CONSOLE_LINKS.exists()


# --------------------------------------------------------------------
# The health cartouche (PLAN-J11 § 11.9) — build_cockpit and the five
# domain functions, duplicated from aistack.cli.health_render.
#
# These do not repeat test_health_render.py's full domain coverage —
# every branch (instrumented/not, clean/alert) is already proven
# there. What is proven here is narrower and specific to the
# duplication: that this module's own copy of each function is
# genuinely wired to a HealthDomain an alert can come from, not a
# copy-paste that silently drifted.
# --------------------------------------------------------------------


def test_build_cockpit_always_names_all_seven_domains(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_STRATEGY", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_CATEGORIZATION", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeDockerProvider(states=[]))

    cockpit = cli.build_cockpit("test-host")

    names = {domain.name for domain in cockpit.domains}
    assert names == {
        "Stockage",
        "Services",
        "Sauvegarde / PRA",
        "GPU",
        "Tests PRA",
        "État persistant",
        "Écarts d'inventaire",
    }


def test_storage_domain_reports_an_alert(monkeypatch, tmp_path):
    mount = tmp_path / "volume"
    mount.mkdir()

    path = tmp_path / "storage_thresholds.yml"
    path.write_text(
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
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", path)

    domain = cli.storage_domain("test-host")

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_services_domain_reports_an_alert(monkeypatch):
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )

    domain = cli.services_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_backup_domain_reports_an_alert(monkeypatch, tmp_path):
    backup_dir = tmp_path / "wordpress"
    backup_dir.mkdir()

    path = tmp_path / "backup_thresholds.yml"
    path.write_text(
        f"""
hosts:
  - host: test-host
    thresholds:
      - path: {backup_dir}
        max_age_days: 7
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", path)

    domain = cli.backup_domain("test-host")

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_technical_debt_score_reports_findings_across_domains(monkeypatch, tmp_path):
    """
    Mirrors `test_health_render.py`'s own
    `test_technical_debt_score_counts_findings_across_every_domain`,
    narrower: only proves this module's own copy of the function is
    genuinely wired, not a repeat of every branch already covered
    there.
    """

    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_STRATEGY", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_CATEGORIZATION", tmp_path / "absent.yml")
    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )

    cockpit = cli.build_cockpit("test-host")
    weights = HealthScoreWeights(weights=(DomainWeight(domain="Services", points=15),))
    score, note = cli.technical_debt_score(cockpit, weights)

    assert note == ""
    assert len(score.findings) == 1
    assert score.value == 85


def test_gpu_domain_reports_an_alert(monkeypatch, tmp_path):
    path = tmp_path / "gpu_thresholds.yml"
    path.write_text(
        """
hosts:
  - host: test-host
    thresholds:
      - kind: temperature_celsius
        celsius: 80
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", path)
    monkeypatch.setattr(
        cli,
        "NvidiaGpuProvider",
        lambda: FakeGpuProvider(
            [
                GpuReading(
                    name="Quadro P400",
                    observed_at=datetime.now(timezone.utc),
                    utilization_percent=1.0,
                    memory_used_mib=142.0,
                    memory_total_mib=2048.0,
                    temperature_celsius=85.0,
                )
            ]
        ),
    )

    domain = cli.gpu_domain("test-host")

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_pra_tests_domain_reports_an_alert(monkeypatch, tmp_path):
    path = tmp_path / "pra_tests.yml"
    path.write_text(
        """
max_age_days: 90
services:
  - name: nextcloud
    last_test: null
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", path)
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_STRATEGY", tmp_path / "absent.yml")

    domain = cli.pra_tests_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_pra_tests_domain_reports_a_not_declared_alert(monkeypatch, tmp_path):
    """
    1.6 tranche 4 (R9, 2026-09-30, OPS-0004's eighth reference case):
    a service `backup_strategy.yml` already declares stateful but
    `pra_tests.yml` does not name at all.
    """

    pra_path = tmp_path / "pra_tests.yml"
    pra_path.write_text(
        """
max_age_days: 90
services:
  - name: nextcloud
    last_test: null
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_PRA_TESTS", pra_path)

    backup_path = tmp_path / "backup_strategy.yml"
    backup_path.write_text(
        """
services:
  - name: nextcloud
    host: GIGABYTE
    has_state: true
    engines: []
    mechanism: null
  - name: wordpress
    host: GIGABYTE
    has_state: true
    engines: []
    mechanism: null
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_STRATEGY", backup_path)

    domain = cli.pra_tests_domain()

    assert domain.instrumented is True
    assert {f.subject for f in domain.findings} == {"nextcloud", "wordpress"}


def test_uncovered_state_domain_reports_an_alert(monkeypatch, tmp_path):
    path = tmp_path / "backup_strategy.yml"
    path.write_text(
        """
services:
  - name: nextcloud
    host: GIGABYTE
    has_state: true
    engines: []
    mechanism: null
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_STRATEGY", path)

    domain = cli.uncovered_state_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1


def test_inventory_gap_domain_reports_an_alert(monkeypatch, tmp_path):
    path = tmp_path / "service_categorization.yml"
    path.write_text(
        """
categories:
  - name: Homelab
    services:
      - name: WordPress
        container: wordpress
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "DEFAULT_CATEGORIZATION", path)
    monkeypatch.setattr(cli, "DEFAULT_NETWORK_DOCKER_OBSERVATION", tmp_path / "absent.json")
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeDockerProvider(states=[]))

    domain = cli.inventory_gap_domain()

    assert domain.instrumented is True
    assert len(domain.findings) == 1


# --------------------------------------------------------------------
# Drift guard — this module's duplicated constants must match
# aistack.cli.health_render's own, the same way health_render.py's own
# threshold paths are already checked against runtime_diagnose.py's.
# --------------------------------------------------------------------


def test_the_default_storage_thresholds_path_matches_health_renders():
    assert cli.DEFAULT_STORAGE_THRESHOLDS == health_render.DEFAULT_STORAGE_THRESHOLDS
    assert cli.DEFAULT_STORAGE_THRESHOLDS.exists()


def test_the_default_backup_thresholds_path_matches_health_renders():
    assert cli.DEFAULT_BACKUP_THRESHOLDS == health_render.DEFAULT_BACKUP_THRESHOLDS
    assert cli.DEFAULT_BACKUP_THRESHOLDS.exists()


def test_the_default_gpu_thresholds_path_matches_health_renders():
    assert cli.DEFAULT_GPU_THRESHOLDS == health_render.DEFAULT_GPU_THRESHOLDS
    assert cli.DEFAULT_GPU_THRESHOLDS.exists()


def test_the_default_health_score_weights_path_matches_health_renders():
    assert (
        cli.DEFAULT_HEALTH_SCORE_WEIGHTS == health_render.DEFAULT_HEALTH_SCORE_WEIGHTS
    )
    assert cli.DEFAULT_HEALTH_SCORE_WEIGHTS.exists()


def test_the_default_pra_tests_path_matches_health_renders():
    assert cli.DEFAULT_PRA_TESTS == health_render.DEFAULT_PRA_TESTS
    assert cli.DEFAULT_PRA_TESTS.exists()


def test_the_default_backup_strategy_path_matches_health_renders():
    assert cli.DEFAULT_BACKUP_STRATEGY == health_render.DEFAULT_BACKUP_STRATEGY
    assert cli.DEFAULT_BACKUP_STRATEGY.exists()


def test_the_default_categorization_path_matches_health_renders():
    assert cli.DEFAULT_CATEGORIZATION == health_render.DEFAULT_CATEGORIZATION
    assert cli.DEFAULT_CATEGORIZATION.exists()


def test_the_default_network_docker_observation_path_matches_health_renders():
    assert (
        cli.DEFAULT_NETWORK_DOCKER_OBSERVATION
        == health_render.DEFAULT_NETWORK_DOCKER_OBSERVATION
    )


def test_technical_debt_score_matches_health_renders_own_behavior(monkeypatch):
    """
    `technical_debt_score` has no path constant to compare (it reuses
    `DEFAULT_HEALTH_SCORE_WEIGHTS`, already checked above) — this
    checks the two duplicated functions still agree on the one thing
    a path comparison cannot: given the same cockpit and weights, the
    same score.
    """

    monkeypatch.setattr(
        cli,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )
    monkeypatch.setattr(
        health_render,
        "DockerProvider",
        lambda: FakeDockerProvider(states=[{"Names": "gluetun", "State": "restarting"}]),
    )

    weights = HealthScoreWeights(weights=(DomainWeight(domain="Services", points=15),))

    console_cockpit = cli.build_cockpit("test-host")
    health_cockpit = health_render.build_cockpit("test-host")

    console_score, console_note = cli.technical_debt_score(console_cockpit, weights)
    health_score, health_note = health_render.technical_debt_score(
        health_cockpit, weights
    )

    assert console_note == health_note == ""
    assert console_score.value == health_score.value
    assert console_score.bucket == health_score.bucket
    assert len(console_score.findings) == len(health_score.findings)
