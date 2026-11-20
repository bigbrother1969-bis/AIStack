"""
Packets the host's firewall refused, read from the counters (ADR-0028 § 2, slice T3b).

`aistack-firewall-snapshot` asks `iptables-save -c` every ten minutes and
appends to `firewall-refusals.jsonl` how many packets each family of
refusing rules has dropped since its counters started: `DOCKER-USER`
(traffic from outside the LAN and the VPN to a published port, by the way
the rule is written), the default policy of `INPUT`, ufw's own rules, and
any other chain. This module turns those running totals into a number for
the last `refusal_window_hours`.

A counter holds no address. The finding says how many packets and which
rule refused them, and says it cannot say who sent them: only the
`DOCKER-USER` refusals are known to come from outside the LAN and the VPN.
Counters start again at a reboot or when the rules are reloaded: a total
that goes down, or a new boot identifier, is taken as a restart from zero,
never as a negative count.

Never past `watch` while the thresholds are not calibrated on real
records; `refusal_watch_per_hour` ships at 0, which keeps the finding to
information until the owner has seen the usual figure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH, Finding

REFUSALS = "firewall-refusals.jsonl"
MAX_AGE = timedelta(hours=2)
# Below this much covered time a rate says nothing: one burst is not a trend.
MIN_COVERED = timedelta(hours=1)
FAMILIES = {
    "docker_user": "from outside the LAN and the VPN, to a published port (DOCKER-USER)",
    "input_policy": "default policy of INPUT, origin not known",
    "ufw": "ufw rules, origin not known",
    "other": "other chains, origin not known",
}


@dataclass(frozen=True)
class Sample:
    at: datetime
    boot: str
    drops: dict[str, int]


def _instant(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_refusals(directory: Path) -> list[Sample] | None:
    """The samples the host unit wrote, oldest first; None when there is no file."""

    try:
        text = (directory / REFUSALS).read_text(encoding="utf-8")
    except OSError:
        return None

    samples = []
    for line in text.splitlines():
        try:
            raw = json.loads(line)
        except ValueError:
            continue
        at = _instant(raw.get("at")) if isinstance(raw, dict) else None
        drops = raw.get("drops") if isinstance(raw, dict) else None
        if at is None or not isinstance(drops, dict):
            continue
        samples.append(Sample(at, str(raw.get("boot", "")), {key: int(value) for key, value in drops.items() if isinstance(value, int)}))
    return sorted(samples, key=lambda sample: sample.at)


def window_counts(samples: list[Sample], start: datetime) -> tuple[dict[str, int], timedelta]:
    """
    Packets refused per family since `start`, and how much time the samples
    cover. The last sample before `start` anchors the first interval when
    there is one; otherwise the window is covered from its first sample.
    """

    before = [sample for sample in samples if sample.at < start]
    used = ([before[-1]] if before else []) + [sample for sample in samples if sample.at >= start]
    counts = {family: 0 for family in FAMILIES}

    for previous, current in zip(used, used[1:], strict=False):
        for family in FAMILIES:
            now_value, then_value = current.drops.get(family, 0), previous.drops.get(family, 0)
            restarted = current.boot != previous.boot or now_value < then_value
            counts[family] += now_value if restarted else now_value - then_value

    covered = used[-1].at - used[0].at if len(used) > 1 else timedelta(0)
    return counts, covered


def assess_refusals(
    samples: list[Sample] | None, now: datetime, definition: SecurityDefinition, snapshot_present: bool = True
) -> list[Finding]:
    """`snapshot_present`: the host unit has written its rules; without it, the report already says the unit is missing."""

    hours = definition.refusal_window_hours

    if samples is None:
        if not snapshot_present:
            return []
        return [
            Finding(
                "refusals.unread",
                INFORMATION,
                "The firewall's refusals are not read from here",
                ("no history yet: install the current aistack-firewall-snapshot (it appends firewall-refusals.jsonl)",),
                unknown="How many packets the firewall refused.",
            )
        ]

    if not samples or now - samples[-1].at > MAX_AGE:
        last = samples[-1].at.isoformat(timespec="minutes") if samples else "never"
        return [
            Finding(
                "refusals.unread",
                INFORMATION,
                "The firewall's refusals history is old",
                (f"last reading {last}: is the host unit still running?",),
                unknown="How many packets the firewall refused since.",
            )
        ]

    counts, covered = window_counts(samples, now - timedelta(hours=hours))

    if covered <= timedelta(0):
        return [
            Finding(
                "refusals.started",
                INFORMATION,
                "The firewall's refusals history has just started",
                ("one reading so far",),
                unknown="How many packets the firewall refused: a second reading is needed.",
            )
        ]

    total = sum(counts.values())
    covered_hours = covered.total_seconds() / 3600
    evidence = tuple(f"{counts[family]} {text}" for family, text in FAMILIES.items() if counts[family]) or ("none",)
    evidence += (f"counted over {covered_hours:.1f} h of the last {hours} h",)
    unknown = "Who sent them: a counter holds no address."
    findings = [
        Finding("refusals.summary", INFORMATION, f"The firewall refused {total} packet(s) in the last {hours} h", evidence, unknown)
    ]

    limit = definition.refusal_watch_per_hour
    if limit and covered >= MIN_COVERED and total / covered_hours >= limit:
        findings.append(
            Finding(
                "refusals.high",
                WATCH,
                f"The firewall refuses {total / covered_hours:.0f} packet(s) an hour, over the {limit} an hour you set",
                evidence,
                unknown,
            )
        )

    return findings
