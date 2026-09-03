from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history
from aistack.priority.apply import ApplyReport


# CPU decision history — the fourth historisation dimension of the
# workstream the owner opened 2026-09-03, scoped 2026-09-03 against
# the gap `claude/ROADMAP-SYNTHESIS-2026-09-03.md` § 2 names:
# `resource_priority_monitor` logs boost/normal transitions to
# stdout (journald) and nothing else — no governed record survives
# the process. This module is that record, decided against two real
# trade-offs put to the owner rather than guessed at:
#
# **Cadence: on change only, not every poll.** The monitor polls
# every `aistack.cli.resource_priority_monitor.POLL_SECONDS` (5s).
# Writing every cycle, kept indefinitely (Observation History's own
# retention decision, reused here on purpose for one queryable
# `aistack.cli.history_query` surface across every historicised
# artifact kind), would be tens of thousands of identical entries a
# day for one that changed. `ApplyReport.changed` is the same
# condition `log_cycle` already prints on — reused, not
# reimplemented, so the two triggers cannot drift apart.
#
# **Content: state and report, not a raw detector reading.** The
# roadmap gap gestures at "why (which detector, what reading)", but
# `aistack.priority.detectors.base.Detector` exposes only
# `is_active() -> bool` — no reading survives past either detector's
# own internals. Answering "what reading" would mean extending that
# shared Protocol and both its implementations
# (`CpuThresholdDetector`, `JellyfinDetector`); the owner chose to
# ship what today's shape already computes — which app, boosted or
# not, and what applying it did — and leave the Protocol alone.
DEFAULT_OUTPUT_PATH = Path("reports/generated/resource-priority-decision.json")


def serialize_decision(
    boosted: Mapping[str, bool],
    report: ApplyReport,
) -> dict[str, Any]:
    """
    The JSON-safe shape one resource-priority decision is
    persisted as.

    Every field here is already computed by `aistack.cli
    .resource_priority_monitor.run_cycle` before this is called —
    nothing is read or derived beyond what the monitor already
    holds in hand. `boosted` names every priority app by its own
    state, the same convention `log_cycle` uses for its printed
    line; `report`'s four outcome buckets are carried through
    unchanged rather than collapsed, so a reader can tell "already
    correct" from "just changed" from "gone" from "Docker refused"
    without re-deriving it.
    """

    return {
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "boosted": dict(boosted),
        "applied": list(report.applied),
        "unchanged": list(report.unchanged),
        "not_found": list(report.not_found),
        "failed": [list(pair) for pair in report.failed],
        "dry_run": report.dry_run,
    }


def record_decision(
    boosted: Mapping[str, bool],
    report: ApplyReport,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path | None:
    """
    Persist one resource-priority decision to history, only when
    `report.changed` — the same condition that already decides
    whether `log_cycle` prints a line. Returns the path written
    (the stable "latest" path, `write_artifact_with_history`'s own
    return convention), or `None` when nothing changed this cycle
    and nothing was written — a caller in a tight poll loop can
    call this every cycle without checking first, the same way it
    already calls `log_cycle` every cycle unconditionally.
    """

    if not report.changed:
        return None

    content = (
        json.dumps(
            serialize_decision(boosted, report),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path
