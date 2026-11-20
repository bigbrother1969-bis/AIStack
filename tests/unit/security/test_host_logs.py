"""Who tried to get in: counted by the host unit, read and judged (ADR-0028 T3c)."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack import host_logs as unit
from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH
from aistack.security.logs import HostLogs, assess_logs, parse_logs, read_logs, read_logs_file

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
VPN = unit.networks(["10.223.207.0/24"])
LAN = unit.networks(list(unit.DEFAULT_LAN))

SSH = [
    "Failed password for root from 203.0.113.9 port 4000 ssh2",
    "Failed password for invalid user admin from 203.0.113.10 port 4001 ssh2",
    "Invalid user admin from 203.0.113.10 port 4001",
    "Failed publickey for big-brother from 192.168.1.20 port 5000 ssh2",
    "Failed password for bob from 10.223.207.2 port 5001 ssh2",
    "Accepted publickey for big-brother from 192.168.1.20 port 5000 ssh2",
    "Failed password for root from not-an-address port 1 ssh2",
]
KERNEL = [
    "DOCKER-USER-REFUSE IN=enp0s31f6 OUT=docker0 SRC=198.51.100.7 DST=172.18.0.5 PROTO=TCP",
    "DOCKER-USER-REFUSE IN=enp0s31f6 OUT=docker0 SRC=2001:db8::1 DST=fd00::5 PROTO=TCP",
    "something else SRC=1.2.3.4",
]


def _npm_line(at: datetime, status: int, host: str, uri: str, client: str, upstream: str = "200") -> str:
    stamp = at.strftime("%d/%b/%Y:%H:%M:%S +0000")
    return f'[{stamp}] - {upstream} {status} - GET https {host} "{uri}" [Client {client}] [Length 12] [Gzip -] [Sent-to 10.0.0.1] "agent" "-"'


def _npm_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "logs"
    directory.mkdir()
    old = NOW - timedelta(hours=30)
    recent = NOW - timedelta(hours=2)
    (directory / "proxy-host-1_access.log").write_text(
        "\n".join(
            [
                _npm_line(recent, 200, "Example.org", "/index.html", "192.168.1.5"),
                _npm_line(recent, 404, "example.org", "/.env", "203.0.113.50"),
                _npm_line(recent, 404, "example.org", "/WP-Login.php?x=1", "203.0.113.51"),
                _npm_line(recent, 502, "example.org", "/a", "192.168.1.5", upstream="502, 200"),
                _npm_line(recent, 301, "other.org", "/a/../../etc/passwd", "10.223.207.2"),
                _npm_line(old, 404, "example.org", "/.git/config", "203.0.113.52"),
                "garbage that is not a log line",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return directory


def test_an_address_is_classed_vpn_then_lan_then_outside() -> None:
    assert unit.origin("10.223.207.2", VPN, LAN) == "vpn"
    assert unit.origin("192.168.1.20", VPN, LAN) == "lan"
    assert unit.origin("::ffff:192.168.1.20", VPN, LAN) == "lan"
    assert unit.origin("203.0.113.9", VPN, LAN) == "outside"
    assert unit.origin("2001:db8::1", VPN, LAN) == "outside"
    assert unit.origin("nobody", VPN, LAN) == "unknown"


def test_ssh_failures_are_counted_by_origin_and_invalid_users_apart() -> None:
    counts = unit.ssh_counts(SSH, VPN, LAN)

    assert counts["failed"] == {"lan": 1, "vpn": 1, "outside": 2, "unknown": 1}
    assert counts["invalid_user"] == {"lan": 0, "vpn": 0, "outside": 1, "unknown": 0}


def test_only_the_docker_user_refusals_of_the_kernel_log_are_counted() -> None:
    assert unit.kernel_counts(KERNEL, VPN, LAN)["docker_user_refuse"] == {"lan": 0, "vpn": 0, "outside": 2, "unknown": 0}


def test_the_proxy_is_counted_per_virtual_host_inside_the_window_only(tmp_path: Path) -> None:
    result = unit.npm_counts(_npm_directory(tmp_path), NOW - timedelta(hours=24), VPN, LAN)

    assert result["requests"] == 5
    zero = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "probes": 0, "probes_ok": 0, "app_paths": 0, "app_paths_ok": 0}
    assert result["vhosts"] == {
        "example.org": {**zero, "2xx": 1, "4xx": 2, "5xx": 1, "probes": 1, "app_paths": 1},
        "other.org": {**zero, "3xx": 1, "probes": 1},
    }
    assert result["probes_by_origin"] == {"lan": 0, "vpn": 1, "outside": 1, "unknown": 0}
    assert result["app_paths_by_origin"] == {"lan": 0, "vpn": 0, "outside": 1, "unknown": 0}


def test_a_probe_and_an_application_path_answered_with_a_success_are_counted_apart(tmp_path: Path) -> None:
    directory = tmp_path / "logs"
    directory.mkdir()
    recent = NOW - timedelta(hours=1)
    (directory / "proxy-host-2_access.log").write_text(
        "\n".join(
            [
                _npm_line(recent, 200, "spa.org", "/.env", "203.0.113.5"),
                _npm_line(recent, 404, "spa.org", "/.git/config", "203.0.113.5"),
                _npm_line(recent, 200, "wp.org", "/xmlrpc.php", "203.0.113.6"),
                _npm_line(recent, 200, "wp.org", "/wp-login.php", "192.168.1.5"),
                _npm_line(recent, 404, "wp.org", "/cgi-bin/x", "203.0.113.6"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = unit.npm_counts(directory, NOW - timedelta(hours=24), VPN, LAN)

    assert result["vhosts"]["spa.org"]["probes"] == 2 and result["vhosts"]["spa.org"]["probes_ok"] == 1
    assert result["vhosts"]["wp.org"]["app_paths"] == 3 and result["vhosts"]["wp.org"]["app_paths_ok"] == 2
    assert result["probes_ok_by_origin"] == {"lan": 0, "vpn": 0, "outside": 1, "unknown": 0}


def test_the_file_holds_counts_and_never_an_address_a_path_or_a_user(tmp_path: Path, monkeypatch) -> None:
    def journal(arguments, since):
        return SSH if arguments == ["_COMM=sshd"] else KERNEL

    monkeypatch.setattr(unit, "_journal", journal)
    report = unit.collect(NOW, VPN, LAN, _npm_directory(tmp_path))
    text = json.dumps(report)

    for secret in ("203.0.113", "192.168.1.20", "10.223.207.2", "198.51.100", "2001:db8", "/.env", "etc/passwd", "admin", "big-brother", "agent", "wp-login", "xmlrpc"):
        assert secret.lower() not in text.lower(), secret
    assert report["sources"] == {"ssh": "ok", "kernel": "ok", "npm": "ok"}


def test_a_source_that_fails_says_so_and_does_not_stop_the_others(tmp_path: Path, monkeypatch) -> None:
    def journal(arguments, since):
        if arguments == ["-k"]:
            raise OSError("Failed to open journal")
        return SSH

    monkeypatch.setattr(unit, "_journal", journal)
    report = unit.collect(NOW, VPN, LAN, None)

    assert report["sources"] == {"ssh": "ok", "kernel": "error: Failed to open journal", "npm": "absent"}
    assert "kernel" not in report


def test_a_journalctl_that_fails_is_an_error_not_an_empty_answer(monkeypatch) -> None:
    monkeypatch.setattr(
        unit.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, 1, stdout="", stderr="no access\n")
    )

    with pytest.raises(OSError, match="no access"):
        unit._journal(["-k"], NOW)


def test_the_unit_writes_the_file_as_the_owner_of_its_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(unit, "_journal", lambda arguments, since: [])
    monkeypatch.setattr(unit.os, "chown", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["aistack-host-logs", "--output", str(tmp_path / "out"), "--vpn", "10.223.207.0/24"])

    assert unit.main() == 0

    assert json.loads((tmp_path / "out" / unit.OUTPUT_NAME).read_text(encoding="utf-8"))["window_hours"] == 24


def test_a_bad_network_is_refused_with_a_message(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["aistack-host-logs", "--output", str(tmp_path), "--vpn", "nonsense"])

    assert unit.main() == 2
    assert "not a network" in capsys.readouterr().err


def test_the_script_uses_the_standard_library_only() -> None:
    tree = ast.parse(Path(unit.__file__).read_text(encoding="utf-8"))
    imported = {
        (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
        for node in ast.walk(tree)
        for alias in (node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else [])
    }

    assert imported <= set(sys.stdlib_module_names)


# -- reading and judging ------------------------------------------------------------------


def _logs(**sections) -> HostLogs:
    sources = {name: "ok" for name in sections}
    return HostLogs(NOW, 24, sources, {"collected_at": NOW.isoformat(), **sections})


def _zero() -> dict[str, int]:
    return {"lan": 0, "vpn": 0, "outside": 0, "unknown": 0}


def test_ssh_failures_are_information_by_default_and_say_how_many_never_who() -> None:
    ssh = {"failed": {**_zero(), "lan": 2, "outside": 5}, "invalid_user": {**_zero(), "outside": 3}}

    [finding] = assess_logs([("local", _logs(ssh=ssh), "")], SecurityDefinition())

    assert finding.key == "logs.ssh" and finding.severity == INFORMATION
    assert "7 failed login(s)" in finding.title
    assert finding.evidence == ("failed: 2 LAN, 5 outside", "unknown user name: 3 outside")
    assert "address" in finding.unknown


def test_the_outside_threshold_makes_it_a_finding_to_watch_and_lan_noise_does_not() -> None:
    definition = SecurityDefinition(ssh_failed_outside_watch=5)
    quiet = {"failed": {**_zero(), "lan": 100, "outside": 4}, "invalid_user": _zero()}
    loud = {"failed": {**_zero(), "outside": 4, "unknown": 1}, "invalid_user": _zero()}

    assert assess_logs([("local", _logs(ssh=quiet), "")], definition)[0].severity == INFORMATION
    assert assess_logs([("local", _logs(ssh=loud), "")], definition)[0].severity == WATCH


def test_a_quiet_host_has_no_finding() -> None:
    quiet = {"failed": _zero(), "invalid_user": _zero()}

    assert assess_logs([("local", _logs(ssh=quiet, kernel={"docker_user_refuse": _zero()}), "")], SecurityDefinition()) == []


def _vhost(**counts: int) -> dict[str, int]:
    base = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "probes": 0, "probes_ok": 0, "app_paths": 0, "app_paths_ok": 0}
    return {**base, **counts}


def _npm(**vhosts: dict[str, int]) -> dict:
    return {
        "requests": 120,
        "vhosts": vhosts,
        "probes_by_origin": {**_zero(), "outside": 3, "vpn": 1},
        "probes_ok_by_origin": _zero(),
        "app_paths_by_origin": {**_zero(), "outside": 500},
    }


def test_the_proxy_counts_probes_and_application_paths_apart_per_virtual_host() -> None:
    npm = _npm(**{"a.org": _vhost(probes=4, app_paths=500, app_paths_ok=450), "b.org": _vhost(**{"5xx": 5})})

    [finding] = assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition(npm_scans_outside_watch=1000))

    assert finding.key == "logs.npm" and finding.severity == INFORMATION
    assert finding.evidence[:2] == ("probes (/.env, /.git…): 1 VPN, 3 outside", "application paths (wp-login, xmlrpc…): 500 outside")
    assert "a.org: 4 probe(s), 0 answered 2xx" in finding.evidence
    assert "a.org: 500 application path request(s), 450 answered 2xx" in finding.evidence
    assert not any("b.org" in line for line in finding.evidence)


def test_the_threshold_counts_probes_and_application_paths_from_outside() -> None:
    npm = _npm(**{"a.org": _vhost(probes=4, app_paths=500)})

    assert assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition(npm_scans_outside_watch=500))[0].severity == WATCH
    assert assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition(npm_scans_outside_watch=503))[0].severity == WATCH
    assert assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition(npm_scans_outside_watch=504))[0].severity == INFORMATION


def test_a_probe_answered_with_a_success_is_to_watch_whatever_the_threshold() -> None:
    npm = _npm(**{"spa.org": _vhost(probes=2, probes_ok=2), "fine.org": _vhost(probes=9)})

    findings = {finding.key: finding for finding in assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition())}

    answered = findings["logs.npm.probe_answered"]
    assert answered.severity == WATCH and answered.evidence == ("spa.org: 2 of 2 probe(s) answered 2xx",)
    assert "single-page" in answered.unknown and "accepted_proxy_hosts" in answered.unknown
    assert findings["logs.npm"].severity == INFORMATION


def test_a_host_accepted_by_name_is_counted_not_reported() -> None:
    npm = _npm(**{"spa.org": _vhost(probes=2, probes_ok=2)})

    keys = [item.key for item in assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition(accepted_proxy_hosts=("spa.org",)))]

    assert "logs.npm.probe_answered" not in keys and "logs.npm" in keys


def test_an_application_path_answered_with_a_success_alone_is_never_a_watch() -> None:
    npm = {**_npm(**{"wp.org": _vhost(app_paths=500, app_paths_ok=500)}), "probes_by_origin": _zero()}

    [finding] = assess_logs([("local", _logs(npm=npm), "")], SecurityDefinition())

    assert finding.key == "logs.npm" and finding.severity == INFORMATION


def test_a_reading_written_before_probes_and_application_paths_were_told_apart_is_still_read() -> None:
    old = {"requests": 100, "vhosts": {"a.org": {"scans": 7, "4xx": 7}}, "scans_by_origin": {**_zero(), "outside": 7}}

    [finding] = assess_logs([("local", _logs(npm=old), "")], SecurityDefinition())

    assert "a.org: 7 probe(s), 0 answered 2xx" in finding.evidence


def test_the_kernel_log_says_it_keeps_at_most_six_a_minute() -> None:
    [finding] = assess_logs([("local", _logs(kernel={"docker_user_refuse": {**_zero(), "outside": 12}}), "")], SecurityDefinition())

    assert finding.key == "logs.kernel" and "12 packet(s)" in finding.title and "six a minute" in finding.unknown


def test_a_source_that_failed_is_a_finding_and_its_numbers_are_not_trusted() -> None:
    logs = HostLogs(NOW, 24, {"ssh": "error: Failed to open journal", "kernel": "ok"}, {"ssh": {"failed": {"lan": 9}}})

    [finding] = assess_logs([("local", logs, "")], SecurityDefinition())

    assert finding.key == "logs.source" and finding.evidence == ("ssh: error: Failed to open journal",)


def test_no_reading_old_or_broken_is_a_finding_about_the_source(tmp_path: Path) -> None:
    (tmp_path / "host-logs.json").write_text(json.dumps({"collected_at": (NOW - timedelta(hours=5)).isoformat(), "sources": {}}), encoding="utf-8")

    old, note_old = read_logs_file(tmp_path, NOW, timedelta(hours=3))
    missing, note_missing = read_logs_file(tmp_path / "nothing", NOW, timedelta(hours=3))
    (tmp_path / "host-logs.json").write_text("{", encoding="utf-8")
    broken, note_broken = read_logs_file(tmp_path, NOW, timedelta(hours=3))

    assert old is None and "old" in note_old and missing is None and "install" in note_missing and broken is None and "readable" in note_broken
    assert [item.key for item in assess_logs([("local", None, note_old)], SecurityDefinition())] == ["logs.unread"]


def test_another_host_is_read_through_its_security_folder_and_named(tmp_path: Path, monkeypatch) -> None:
    folder = tmp_path / "hosts" / "pi" / "security"
    folder.mkdir(parents=True)
    payload = {"collected_at": NOW.isoformat(), "window_hours": 24, "sources": {"ssh": "ok"}, "ssh": {"failed": {**_zero(), "outside": 2}, "invalid_user": _zero()}}
    (folder / "host-logs.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "hosts.yml").write_text(
        f"silent_after_minutes: 1500\nhosts:\n  pi:\n    directory: {folder.parent}\n  absent:\n    directory: {tmp_path / 'nowhere'}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AISTACK_CONFIG_DIR", str(tmp_path))

    hosts = read_logs(tmp_path / "security-host", tmp_path, NOW)

    assert [name for name, _, _ in hosts] == ["local", "pi"]
    findings = assess_logs(hosts, SecurityDefinition())
    assert [finding.key for finding in findings] == ["logs.unread", "logs.pi.ssh"]
    assert findings[1].title.startswith("pi: SSH")


def test_parse_accepts_only_a_dated_reading() -> None:
    assert parse_logs("{}") is None and parse_logs("nonsense") is None
    assert parse_logs(json.dumps({"collected_at": "2026-11-20T12:00:00+00:00"})) is not None


def test_the_declaration_reads_the_two_thresholds_and_the_accepted_hosts(tmp_path: Path) -> None:
    from aistack.security.yaml import load_security_yaml

    path = tmp_path / "s.yml"
    path.write_text("ssh_failed_outside_watch: 20\nnpm_scans_outside_watch: 100\naccepted_proxy_hosts:\n  - spa.org\n", encoding="utf-8")
    bad = tmp_path / "b.yml"
    bad.write_text("ssh_failed_outside_watch: -1\n", encoding="utf-8")

    definition = load_security_yaml(path)

    assert (definition.ssh_failed_outside_watch, definition.npm_scans_outside_watch) == (20, 100)
    assert definition.accepted_proxy_hosts == ("spa.org",)
    with pytest.raises(ValueError, match="ssh_failed_outside_watch"):
        load_security_yaml(bad)
