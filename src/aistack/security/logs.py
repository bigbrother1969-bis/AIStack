"""
Who tried to get in, read from the counts a host unit wrote (ADR-0028 § 2, slice T3c).

The assessment runs in a container that has neither the host's journal
nor the proxy's logs. A small root unit on each host (`aistack-host-logs`)
counts, over the last 24 hours and by kind of network (the LAN, the VPN,
outside), the failed SSH logins, the packets `DOCKER-USER` refused and
logged, and the requests Nginx Proxy Manager answered by status class and
the scanner-looking ones. This module reads those counts and judges them.

A finding carries counts and names of virtual hosts, never an address, a
path, a user name or a line of a log: the unit did not write any. A
source that failed, or a host that wrote nothing recently, is a finding
about the source, never a quiet host.

Information by default and never past `watch`: `ssh_failed_outside_watch`
and `npm_scans_outside_watch` ship at 0 (off), to be set above the figure
you have seen in the report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH, Finding

LOGS = "host-logs.json"
MAX_AGE = timedelta(hours=3)
# Same reason as the other snapshots of a host that may be off for a day (ADR-0020).
REMOTE_MAX_AGE = timedelta(hours=25)
REMOTE_DIRECTORY = "security"
CLASSES = ("lan", "vpn", "outside", "unknown")
LABELS = {"lan": "LAN", "vpn": "VPN", "outside": "outside", "unknown": "unknown origin"}


@dataclass(frozen=True)
class HostLogs:
    collected_at: datetime
    window_hours: int
    sources: dict[str, str]
    data: dict[str, Any]


def _counts(value: Any) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    return {name: raw[name] if isinstance(raw.get(name), int) else 0 for name in CLASSES}


def parse_logs(text: str) -> HostLogs | None:
    try:
        raw = json.loads(text)
        collected = datetime.fromisoformat(str(raw["collected_at"]))
    except (ValueError, KeyError, TypeError):
        return None

    sources = raw.get("sources")
    return HostLogs(
        collected if collected.tzinfo else collected.replace(tzinfo=timezone.utc),
        raw["window_hours"] if isinstance(raw.get("window_hours"), int) else 24,
        {str(key): str(value) for key, value in sources.items()} if isinstance(sources, dict) else {},
        raw,
    )


def read_logs_file(directory: Path, now: datetime, max_age: timedelta) -> tuple[HostLogs | None, str]:
    """The counts a host unit wrote, and a sentence saying why there are none (empty when fresh)."""

    try:
        text = (directory / LOGS).read_text(encoding="utf-8")
    except OSError:
        return None, "no logs reading yet: install the host unit aistack-host-logs"

    reading = parse_logs(text)
    if reading is None:
        return None, f"{LOGS} is not readable"

    if now - reading.collected_at > max_age:
        return None, f"{LOGS} is old ({reading.collected_at.isoformat(timespec='minutes')}): is the host unit still running?"

    return reading, ""


def read_logs(
    local_directory: Path, generated_dir: Path, now: datetime | None = None
) -> list[tuple[str, HostLogs | None, str]]:
    """
    This host's counts (`local`) and those of the other traced hosts, which
    reach `<directory>/security/` through the push of ADR-0020. A traced host
    with no such folder, or no such file, is not reported: it may not run the unit.
    """

    from aistack.hosts.records import load_hosts_declaration

    now = now or datetime.now(timezone.utc)
    found: list[tuple[str, HostLogs | None, str]] = [("local", *read_logs_file(local_directory, now, MAX_AGE))]

    try:
        hosts = load_hosts_declaration(generated_dir).hosts
    except (OSError, ValueError, AttributeError):
        return found

    for host in hosts:
        folder = host.directory / REMOTE_DIRECTORY
        if (folder / LOGS).is_file():
            found.append((host.name, *read_logs_file(folder, now, REMOTE_MAX_AGE)))

    return found


def _split(counts: dict[str, int]) -> str:
    return ", ".join(f"{counts[name]} {LABELS[name]}" for name in CLASSES if counts[name]) or "none"


def assess_one(logs: HostLogs | None, note: str, definition: SecurityDefinition) -> list[Finding]:
    if logs is None:
        return [
            Finding(
                "logs.unread",
                INFORMATION,
                "The host's logs are not read from here",
                (note or "no logs reading",),
                unknown="Who tried to get in: failed logins, refused packets, scanner requests.",
            )
        ]

    findings: list[Finding] = []
    hours = logs.window_hours
    errors = [f"{name}: {state}" for name, state in sorted(logs.sources.items()) if state.startswith("error")]

    if errors:
        findings.append(
            Finding(
                "logs.source",
                INFORMATION,
                "A log source could not be read on the host",
                tuple(errors),
                unknown="What that source says; a source that fails is not a quiet one.",
            )
        )

    ssh = logs.data.get("ssh")
    if logs.sources.get("ssh") == "ok" and isinstance(ssh, dict):
        failed, invalid = _counts(ssh.get("failed")), _counts(ssh.get("invalid_user"))
        if sum(failed.values()) or sum(invalid.values()):
            limit = definition.ssh_failed_outside_watch
            outside = failed["outside"] + failed["unknown"]
            findings.append(
                Finding(
                    "logs.ssh",
                    WATCH if limit and outside >= limit else INFORMATION,
                    f"SSH: {sum(failed.values())} failed login(s) in the last {hours} h",
                    (f"failed: {_split(failed)}", f"unknown user name: {_split(invalid)}"),
                    unknown="Which account was aimed at and from which address: the unit counts, it keeps neither.",
                )
            )

    npm = logs.data.get("npm")
    if logs.sources.get("npm") == "ok" and isinstance(npm, dict):
        raw_vhosts = npm.get("vhosts")
        vhosts = raw_vhosts if isinstance(raw_vhosts, dict) else {}
        scans = _counts(npm.get("scans_by_origin"))
        requests = npm.get("requests") if isinstance(npm.get("requests"), int) else 0
        limit = definition.npm_scans_outside_watch
        scanned = sorted(
            ((name, row) for name, row in vhosts.items() if isinstance(row, dict) and row.get("scans")),
            key=lambda item: -int(item[1].get("scans", 0)),
        )
        if requests and (sum(scans.values()) or scanned):
            lines = [f"scanner-looking requests: {_split(scans)}"] + [
                f"{name}: {row.get('scans', 0)} scanner-looking, {row.get('4xx', 0)} in 4xx, {row.get('5xx', 0)} in 5xx"
                for name, row in scanned
            ]
            findings.append(
                Finding(
                    "logs.npm",
                    WATCH if limit and scans["outside"] + scans["unknown"] >= limit else INFORMATION,
                    f"Proxy: {sum(scans.values())} scanner-looking request(s) among {requests} in the last {hours} h",
                    tuple(lines[: definition.max_listed + 1]),
                    unknown="What was asked and by whom: the unit counts, it keeps neither the path nor the address.",
                )
            )

    kernel = logs.data.get("kernel")
    if logs.sources.get("kernel") == "ok" and isinstance(kernel, dict):
        refused = _counts(kernel.get("docker_user_refuse"))
        if sum(refused.values()):
            findings.append(
                Finding(
                    "logs.kernel",
                    INFORMATION,
                    f"DOCKER-USER refused and logged {sum(refused.values())} packet(s) in the last {hours} h",
                    (f"by origin: {_split(refused)}",),
                    unknown="How many were refused in all: the log keeps at most six a minute, the firewall's counters count them all.",
                )
            )

    return findings


def assess_logs(hosts: list[tuple[str, HostLogs | None, str]], definition: SecurityDefinition) -> list[Finding]:
    """The same judgement for each host, each finding naming its host (this one has no prefix)."""

    findings: list[Finding] = []
    for name, logs, note in hosts:
        for finding in assess_one(logs, note, definition):
            if name == "local":
                findings.append(finding)
            else:
                findings.append(replace(finding, key=finding.key.replace("logs.", f"logs.{name}.", 1), title=f"{name}: {finding.title}"))
    return findings
