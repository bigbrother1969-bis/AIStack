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
    # host runs this suite, `main()` still writes all four domains.
    assert "État de santé du homelab" in document


def test_main_prints_a_confirmation_line(workspace, capsys):
    cli.main()

    captured = capsys.readouterr()
    assert "Console written to" in captured.out
    assert "6 link(s)" in captured.out
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
# The health cartouche (PLAN-J11 § 11.9) — build_cockpit and the four
# domain functions, duplicated from aistack.cli.health_render.
#
# These do not repeat test_health_render.py's full domain coverage —
# every branch (instrumented/not, clean/alert) is already proven
# there. What is proven here is narrower and specific to the
# duplication: that this module's own copy of each function is
# genuinely wired to a HealthDomain an alert can come from, not a
# copy-paste that silently drifted.
# --------------------------------------------------------------------


def test_build_cockpit_always_names_all_four_domains(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "DEFAULT_STORAGE_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_BACKUP_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DEFAULT_GPU_THRESHOLDS", tmp_path / "absent.yml")
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeDockerProvider(states=[]))

    cockpit = cli.build_cockpit("test-host")

    names = {domain.name for domain in cockpit.domains}
    assert names == {"Stockage", "Services", "Sauvegarde / PRA", "GPU"}


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
