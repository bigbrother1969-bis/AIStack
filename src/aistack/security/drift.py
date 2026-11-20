"""
What changed on the traced hosts, read from the `ADR-0020` records (ADR-0028 § 2, slice T3a).

The host collectors already write, for each host `hosts.yml` traces, an
`events.jsonl` of files added, modified or removed (with a fingerprint), of
units enabled or disabled, and of apt runs. This module reads the last
`drift_window_hours` of it and judges it. It changes nothing and reads no
file's content: a finding names a path and what happened to it, never a
fingerprint or a content.

Judgement (the severity never goes past `watch` while the thresholds are
not calibrated on real records):
- a change to a sensitive path (accounts, privilege, SSH, firewall, VPN,
  UPS, tunnel, hand-installed programs, scheduled jobs) or a unit newly
  enabled is to watch, unless an apt run on that host explains it;
- noise (printer queue, hardware clock, `*.dpkg-new`…) and the paths the
  owner accepts (`accepted_drift`) are counted, never reported;
- every other change is a count in one information finding;
- a host that does not report, or whose records cannot be read, is a
  finding about the source (information: the console's host health
  already raises a silent collector), never a silence.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from aistack.hosts.records import HostRecords, HostsDeclaration
from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH, Finding

ENABLED = ("enabled", "enabled-runtime", "linked", "linked-runtime")
# An apt run whose end was not recorded is taken to last this long.
OPEN_APT = timedelta(minutes=30)


def _instant(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _apt_windows(events: list[dict[str, Any]], grace: timedelta) -> list[tuple[datetime, datetime]]:
    """When an apt run could explain a change. The collector notes a change
    when it next runs, so each window is extended by the collector's grace."""

    windows = []
    for event in events:
        if event.get("kind") != "apt":
            continue
        start = _instant(event.get("at"))
        if start is None:
            continue
        end = _instant(event.get("ended")) if event.get("ended") else None
        windows.append((start, (end or start + OPEN_APT) + grace))
    return windows


def _explained(at: datetime, windows: list[tuple[datetime, datetime]]) -> bool:
    return any(start <= at <= end for start, end in windows)


def _listed(lines: list[str], limit: int) -> tuple[str, ...]:
    return tuple(lines) if len(lines) <= limit else (*lines[:limit], f"and {len(lines) - limit} more")


@dataclass(frozen=True)
class Counted:
    """What the records of one host say over the window, sorted into classes."""

    recent: list[dict[str, Any]]
    reported: list[str]
    explained: int
    ignored: int
    ordinary: int
    units: int

    @property
    def files(self) -> int:
        return sum(1 for event in self.recent if event.get("kind") == "file")

    @property
    def runs(self) -> int:
        return sum(1 for event in self.recent if event.get("kind") == "apt")


def classify(records: HostRecords, now: datetime, definition: SecurityDefinition) -> Counted:
    since = now - timedelta(hours=definition.drift_window_hours)
    grace = timedelta(minutes=definition.drift_apt_grace_minutes)
    recent: list[dict[str, Any]] = []

    for _, event in records.events:
        at = _instant(event.get("at"))
        if at is not None and since <= at <= now:
            recent.append(event)

    windows = _apt_windows(recent, grace)
    reported: list[str] = []
    explained = ignored = ordinary = units = 0

    for event in recent:
        at = _instant(event.get("at"))
        kind = event.get("kind")

        if at is None:
            continue

        if kind == "file":
            path, action = str(event.get("path", "")), str(event.get("action", ""))
            if _matches(path, definition.drift_noise) or _matches(path, definition.accepted_drift):
                ignored += 1
            elif not _matches(path, definition.drift_sensitive):
                ordinary += 1
            elif _explained(at, windows):
                explained += 1
            else:
                reported.append(f"{action} {path}")
        elif kind == "unit":
            units += 1
            unit = str(event.get("unit", ""))
            if event.get("after") in ENABLED and event.get("before") not in ENABLED:
                if _explained(at, windows):
                    explained += 1
                else:
                    reported.append(f"unit enabled {unit}")

    return Counted(recent, reported, explained, ignored, ordinary, units)


def host_counts(records: HostRecords, silent_after: timedelta, now: datetime, definition: SecurityDefinition) -> dict[str, int] | None:
    """The numbers behind one host's drift findings; None when the host cannot be judged (unread, silent)."""

    if records.problem or records.silent(now, silent_after):
        return None

    counted = classify(records, now, definition)
    return {
        "sensitive": len(set(counted.reported)),
        "explained": counted.explained,
        "other": counted.ordinary,
        "noise": counted.ignored,
        "units": counted.units,
        "apt_runs": counted.runs,
    }


def assess_host_drift(records: HostRecords, silent_after: timedelta, now: datetime, definition: SecurityDefinition) -> list[Finding]:
    name = records.host

    if records.problem:
        return [
            Finding(
                f"drift.{name}.unread",
                INFORMATION,
                f"{name}: the host's change records cannot be read",
                (records.problem,),
                unknown="Whether files or units changed on this host; nothing was judged.",
            )
        ]

    if records.silent(now, silent_after):
        last = records.last_run
        return [
            Finding(
                f"drift.{name}.silent",
                INFORMATION,
                f"{name}: the host's collector has not reported for a long time",
                (f"last run {last.isoformat(timespec='minutes')}" if last else "no run recorded",),
                unknown="Whether files or units changed on this host since; nothing was judged.",
            )
        ]

    counted = classify(records, now, definition)
    reported, explained, ignored, ordinary, units = (
        counted.reported, counted.explained, counted.ignored, counted.ordinary, counted.units
    )
    recent = counted.recent

    findings: list[Finding] = []

    if reported:
        findings.append(
            Finding(
                f"drift.{name}.sensitive",
                WATCH,
                f"{name}: {len(reported)} sensitive change(s) in the last {definition.drift_window_hours} h",
                _listed(sorted(set(reported)), definition.max_listed),
                unknown="Who made the change and why; only the path and the action are read, never the content.",
            )
        )

    runs, files = counted.runs, counted.files

    if recent and (files or units or runs):
        findings.append(
            Finding(
                f"drift.{name}.summary",
                INFORMATION,
                f"{name}: {files} file change(s), {units} unit change(s), {runs} apt run(s) in the last {definition.drift_window_hours} h",
                (
                    f"{ordinary} other file change(s)",
                    f"{explained} sensitive change(s) explained by an apt run",
                    f"{ignored} counted as noise or accepted",
                ),
                unknown="What the other changes are.",
            )
        )

    return findings


def assess_drift(
    records: list[HostRecords], declaration: HostsDeclaration | None, now: datetime, definition: SecurityDefinition
) -> list[Finding]:
    if declaration is None:
        return []

    findings: list[Finding] = []
    for host in records:
        findings += assess_host_drift(host, declaration.silent_after, now, definition)
    return findings
