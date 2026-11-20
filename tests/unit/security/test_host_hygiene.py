"""The host's packages and sensitive files: collected, read and judged (ADR-0028 T2c)."""

from __future__ import annotations

import ast
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack import host_hygiene as collector
from aistack.security.definition import SecurityDefinition
from aistack.security.findings import FIX, INFORMATION, WATCH
from aistack.security.host import (
    FILES,
    PACKAGES,
    HostFiles,
    SensitiveFile,
    assess_files,
    assess_packages,
    parse_files,
    parse_packages,
    read_host,
)
from aistack.security.yaml import load_security_yaml

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
STAMP = NOW.isoformat(timespec="seconds")
SIMULATION = """Reading package lists...
Inst libssl3 [3.0.1] (3.0.2 Debian-Security:12/stable-security [amd64])
Inst curl [7.1] (7.2 Debian:12.5/stable [amd64])
Inst linux-image-6 (6.1.0 Debian:12/stable [amd64])
Conf libssl3 (3.0.2 Debian-Security:12/stable-security [amd64])
"""


def _packages(upgrades: str = "", reboot: str = "no", lists: str = "2026-11-19T06:00:00+00:00"):
    text = f"# aistack-collected-at: {STAMP}\nupgradable: 0\nsecurity: 0\nreboot-required-since: {reboot}\nlists-updated: {lists}\n{upgrades}"
    packages = parse_packages(text)
    assert packages is not None
    return packages


def test_the_simulation_gives_the_upgrades_and_the_security_ones_only() -> None:
    assert collector.parse_simulation(SIMULATION) == [
        ("libssl3", "3.0.1", "3.0.2", True),
        ("curl", "7.1", "7.2", False),
    ]


def test_a_security_update_is_to_watch_and_names_the_package() -> None:
    packages = _packages("package: libssl3 3.0.1 3.0.2 security\npackage: curl 7.1 7.2 other\n")

    findings = {item.key: item for item in assess_packages(packages, "", NOW, SecurityDefinition())}

    assert findings["host.updates.security"].severity == WATCH
    assert findings["host.updates.security"].evidence == ("libssl3 3.0.1 -> 3.0.2",)
    assert findings["host.updates.pending"].severity == INFORMATION


def test_a_host_up_to_date_has_no_finding() -> None:
    assert assess_packages(_packages(), "", NOW, SecurityDefinition()) == []


def test_a_reboot_is_information_then_a_finding_to_watch_past_the_limit() -> None:
    recent = (NOW - timedelta(days=3)).isoformat()
    late = (NOW - timedelta(days=20)).isoformat()

    assert assess_packages(_packages(reboot=recent), "", NOW, SecurityDefinition())[0].severity == INFORMATION
    assert assess_packages(_packages(reboot=late), "", NOW, SecurityDefinition())[0].severity == WATCH
    assert assess_packages(_packages(reboot=late), "", NOW, SecurityDefinition(max_reboot_pending_days=30))[0].severity == INFORMATION


def test_old_package_lists_are_to_watch() -> None:
    old = (NOW - timedelta(days=10)).isoformat()

    findings = assess_packages(_packages(lists=old), "", NOW, SecurityDefinition())

    assert [(item.key, item.severity) for item in findings] == [("host.apt.stale", WATCH)]


def test_no_reading_is_said_not_guessed() -> None:
    findings = assess_packages(None, "no host snapshot yet", NOW, SecurityDefinition())

    assert findings[0].severity == INFORMATION and findings[0].unknown


def test_other_access_to_a_secret_is_to_fix_and_group_access_to_watch() -> None:
    files = HostFiles(
        NOW,
        (
            SensitiveFile(0o644, "root", "root", "/srv/a/.env"),
            SensitiveFile(0o640, "root", "docker", "/srv/b/.env"),
            SensitiveFile(0o600, "root", "root", "/srv/c/.env"),
        ),
    )

    findings = {item.key: item for item in assess_files(files, SecurityDefinition())}

    assert findings["host.files.exposed"].severity == FIX
    assert findings["host.files.exposed"].evidence == ("/srv/a/.env: 0644 root:root",)
    assert findings["host.files.group"].severity == WATCH
    assert findings["host.files.group"].evidence == ("/srv/b/.env: 0640 root:docker",)
    assert len(findings) == 2


def test_an_accepted_file_is_counted_not_reported() -> None:
    files = HostFiles(NOW, (SensitiveFile(0o644, "root", "root", "/srv/a/.env"),))

    findings = assess_files(files, SecurityDefinition(accepted_files=("/srv/a/.env",)))

    assert [(item.key, item.severity) for item in findings] == [("host.files.accepted", INFORMATION)]


def test_the_files_are_read_back_with_their_rights() -> None:
    text = f"# aistack-collected-at: {STAMP}\n0600 root root /etc/ssh/ssh_host_rsa_key\nbroken\nzzzz a b /x\n0644 big-brother big-brother /srv/my dir/.env\n"

    files = parse_files(text)

    assert files is not None and [(item.mode, item.path) for item in files.files] == [
        (0o600, "/etc/ssh/ssh_host_rsa_key"),
        (0o644, "/srv/my dir/.env"),
    ]


def test_a_reading_without_a_date_or_too_old_is_set_aside(tmp_path: Path) -> None:
    (tmp_path / PACKAGES).write_text("upgradable: 1\n", encoding="utf-8")
    (tmp_path / FILES).write_text(f"# aistack-collected-at: {(NOW - timedelta(hours=5)).isoformat()}\n", encoding="utf-8")

    packages, files, note = read_host(tmp_path, NOW)

    assert packages is None and files is None
    assert "has no date" in note and "is old" in note


def test_a_missing_directory_asks_for_the_host_unit(tmp_path: Path) -> None:
    assert read_host(tmp_path, NOW)[2].startswith("no host snapshot yet")


def test_the_security_declaration_validates_the_new_keys(tmp_path: Path) -> None:
    path = tmp_path / "security.yml"
    path.write_text("max_reboot_pending_days: 30\nmax_apt_age_days: 3\naccepted_files:\n  - /srv/a/.env\n", encoding="utf-8")

    definition = load_security_yaml(path)

    assert (definition.max_reboot_pending_days, definition.max_apt_age_days, definition.accepted_files) == (30, 3, ("/srv/a/.env",))

    for bad in ("max_apt_age_days: 0\n", "accepted_files: [relative/path]\n", "max_reboot_pending_days: true\n"):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ValueError):
            load_security_yaml(path)


def test_the_collector_lists_rights_and_never_content(tmp_path: Path, monkeypatch) -> None:
    secret = tmp_path / ".env"
    secret.write_text("PASSWORD=hunter2\n", encoding="utf-8")
    secret.chmod(0o640)
    (tmp_path / "id_rsa.pub").write_text("public", encoding="utf-8")

    text = collector.files_text((str(tmp_path / ".env"), str(tmp_path / "*.pub")))

    assert text.count("\n") == 1 and "0640" in text and str(secret) in text
    assert "hunter2" not in text


def test_a_failed_simulation_removes_the_old_packages_file(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / collector.PACKAGES).write_text("old", encoding="utf-8")
    monkeypatch.setattr(collector, "_simulate", lambda: None)
    monkeypatch.setattr(collector.os, "chown", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["aistack-host-hygiene", "--output", str(tmp_path), "--glob", str(tmp_path / "none")])

    assert collector.main() == 0
    assert not (tmp_path / collector.PACKAGES).exists()
    assert (tmp_path / collector.FILES).read_text(encoding="utf-8").startswith(collector.HEADER)


def test_the_collector_changes_nothing_and_runs_only_what_reads() -> None:
    source = Path(collector.__file__).read_text(encoding="utf-8")
    calls = [
        [ast.literal_eval(element) for element in node.args[0].elts if isinstance(element, ast.Constant)]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "run"
    ]

    assert calls == [["apt-get", "-s", "-o", "Debug::NoLocking=1", "dist-upgrade"]]
    assert "install" not in source.split("def _simulate")[1].split("def _iso")[0].replace("dist-upgrade", "")


def test_the_unit_reads_only_and_keeps_its_hardening() -> None:
    unit = Path("deploy/host-hygiene/aistack-host-hygiene.service").read_text(encoding="utf-8")

    for line in ("ProtectSystem=strict", "NoNewPrivileges=yes", "PrivateTmp=yes", "CapabilityBoundingSet=CAP_DAC_READ_SEARCH"):
        assert line in unit
