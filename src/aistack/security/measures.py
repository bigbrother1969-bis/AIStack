"""
The numbers behind one assessment (ADR-0028 slice T4a).

A finding says what is wrong; a graph needs how much, again and again. This
module turns what the assessment read into a flat map of integers, which the
report keeps (`measures`) and the vigil appends to `security-series.jsonl`
at each pass. Counts only: never an address, a path, a user name, a
fingerprint or a content, which is also why a name here is a class (`lan`,
`vpn`, `outside`), a host or a virtual host the owner declared himself.

Each key is `family.subject.measure`, in lower case. A source that was not
read adds no key: a gap in a graph is the truth, a zero would be a lie.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from aistack.hosts.records import HostRecords, HostsDeclaration
from aistack.security.definition import SecurityDefinition
from aistack.security.drift import host_counts
from aistack.security.findings import SEVERITIES, Finding
from aistack.security.host import Packages
from aistack.security.logs import CLASSES, HostLogs
from aistack.security.refusals import Sample, window_counts


def _whole(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _by_class(value: Any) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    return {name: _whole(raw.get(name)) for name in CLASSES}


def _name(text: str) -> str:
    """A subject as it goes into a key: no dot, no space."""

    return "".join(char if char.isalnum() or char in "-_" else "_" for char in text.lower()) or "unknown"


def _findings(findings: list[Finding]) -> dict[str, int]:
    found = {f"findings.{severity}": sum(1 for item in findings if item.severity == severity) for severity in SEVERITIES}

    for item in findings:
        area = _name(item.key.split(".")[0])
        key = f"area.{area}.{item.severity}"
        found[key] = found.get(key, 0) + 1

    return found


def _logs(host: str, logs: HostLogs) -> dict[str, int]:
    found: dict[str, int] = {}
    subject = _name(host)
    ssh, kernel, npm = logs.data.get("ssh"), logs.data.get("kernel"), logs.data.get("npm")

    if logs.sources.get("ssh") == "ok" and isinstance(ssh, dict):
        for name, value in _by_class(ssh.get("failed")).items():
            found[f"ssh.{subject}.failed.{name}"] = value
        for name, value in _by_class(ssh.get("invalid_user")).items():
            found[f"ssh.{subject}.invalid_user.{name}"] = value

    if logs.sources.get("kernel") == "ok" and isinstance(kernel, dict):
        for name, value in _by_class(kernel.get("docker_user_refuse")).items():
            found[f"kernel.{subject}.docker_user_refuse.{name}"] = value

    if logs.sources.get("npm") == "ok" and isinstance(npm, dict):
        found[f"npm.{subject}.requests"] = _whole(npm.get("requests"))
        probes = _by_class(npm.get("probes_by_origin") or npm.get("scans_by_origin"))
        paths = _by_class(npm.get("app_paths_by_origin"))
        for name in CLASSES:
            found[f"npm.{subject}.probes.{name}"] = probes[name]
            found[f"npm.{subject}.app_paths.{name}"] = paths[name]

        vhosts = npm.get("vhosts")
        rows = [row for row in vhosts.values() if isinstance(row, dict)] if isinstance(vhosts, dict) else []
        found[f"npm.{subject}.probes_answered"] = sum(_whole(row.get("probes_ok")) for row in rows)
        found[f"npm.{subject}.app_paths_answered"] = sum(_whole(row.get("app_paths_ok")) for row in rows)

    return found


def _packages(host: str, packages: Packages, now: datetime) -> dict[str, int]:
    subject = _name(host)
    found = {
        f"packages.{subject}.updates": len(packages.upgrades),
        f"packages.{subject}.security": sum(1 for upgrade in packages.upgrades if upgrade.security),
    }

    if packages.reboot_since is not None:
        found[f"packages.{subject}.reboot_days"] = max((now - packages.reboot_since) // timedelta(days=1), 0)

    return found


def measures(
    *,
    findings: list[Finding],
    listening: int,
    published: int | None,
    refusals: list[Sample] | None,
    logs: list[tuple[str, HostLogs | None, str]],
    drift: tuple[list[HostRecords], HostsDeclaration | None],
    packages: list[tuple[str, Packages | None]],
    old_images: int | None,
    now: datetime,
    definition: SecurityDefinition,
) -> dict[str, int]:
    found = _findings(findings)
    found["ports.listening"] = listening

    if published is not None:
        found["ports.published"] = published

    if refusals:
        counts, covered = window_counts(refusals, now - timedelta(hours=definition.refusal_window_hours))
        for family, value in counts.items():
            found[f"refusals.{_name(family)}"] = value
        found["refusals.covered_minutes"] = int(covered.total_seconds() // 60)

    for host, host_logs, _note in logs:
        if host_logs is not None:
            found.update(_logs(host, host_logs))

    records, declaration = drift
    if declaration is not None:
        for host_records in records:
            counted = host_counts(host_records, declaration.silent_after, now, definition)
            if counted is not None:
                for name, value in counted.items():
                    found[f"drift.{_name(host_records.host)}.{name}"] = value

    for host, host_packages in packages:
        if host_packages is not None:
            found.update(_packages(host, host_packages, now))

    if old_images is not None:
        found["images.old"] = old_images

    return dict(sorted(found.items()))
