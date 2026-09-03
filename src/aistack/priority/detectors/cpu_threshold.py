from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CpuStreakState:
    """
    What `resolve_cpu_active` remembers between two polls, and
    nothing more.

    `above_since` is a `time.monotonic()` reading, never a wall
    clock — the same reasoning `aistack.priority.grace.GraceState`
    already carries for its own timestamp: a system clock
    adjustment must not manufacture or erase a streak. `None` means
    "not currently above threshold": either the container has never
    been seen above it, or a poll already found it back below.
    """

    above_since: float | None = None


def resolve_cpu_active(
    usage_percent: float,
    threshold_percent: float,
    sustained_seconds: float,
    now: float,
    state: CpuStreakState,
) -> tuple[bool, CpuStreakState]:
    """
    Whether this poll's CPU reading counts as "active", and the
    state to carry into the next one.

    **Pure, and separate from `CpuThresholdDetector` on purpose** —
    same split as `resolve_boosted`/`GraceState`: `now` and `state`
    arrive as plain values rather than being read from the clock in
    here, so a fifteen-second streak is tested in a heartbeat
    instead of a test that actually waits fifteen seconds.

    **Debounces the way up, not the way down — the opposite of
    `resolve_boosted`.** A CPU reading is a noisy proxy for "someone
    is using this application": a two-second spike from a cron job
    must not read as active, so the usage has to stay at or above
    `threshold_percent` for `sustained_seconds` continuously before
    this returns `True`. There is no debounce on the way down here;
    `aistack.priority.grace.resolve_boosted`, layered on top of
    this detector's own `is_active()` answer by the monitor loop,
    already smooths the way down for every priority app alike — a
    second debounce here would only hide how long the real streak
    was.

    **One reading below threshold resets the streak entirely,
    rather than tolerating a brief dip.** A container legitimately
    busy for fifteen seconds with one two-second lull is, in
    practice, still "in use" — but treating a dip as "still
    streaking" would need its own grace period, layered under a
    detector whose only job is to answer one question for one poll.
    The 5-second poll interval (`aistack.cli.
    resource_priority_monitor.POLL_SECONDS`) means a genuinely busy
    container restarts a fifteen-second streak within a few polls of
    any such dip — accepted, not measured against a real
    non-Jellyfin priority app yet (this detector's own numbers are
    still the owner's starting guess, per
    `CpuThresholdDetectorDefinition`'s docstring).
    """

    if usage_percent >= threshold_percent:
        since = state.above_since if state.above_since is not None else now
        return (now - since) >= sustained_seconds, CpuStreakState(above_since=since)

    return False, CpuStreakState(above_since=None)


class CpuThresholdDetector:
    """
    Detect activity by a container's own live CPU usage, sustained.

    Conforms to `aistack.priority.detectors.base.Detector`. Reads
    `docker stats --no-stream`, the same family of call
    `aistack.providers.docker.provider.DockerProvider` already makes
    for other facts, and folds the reading through
    `resolve_cpu_active`, carrying its own `CpuStreakState` between
    polls — this class's only state, mutated in place the same way
    `aistack.cli.resource_priority_monitor.main`'s own loop already
    carries `GraceState` from one poll to the next.

    **Unreadable reads as 0% — not active, decision #4's own
    reasoning extended to a second detector type.** A container that
    has stopped, been removed, or a `docker stats` call that fails
    for any other reason is not this feature misbehaving; it must
    not be read as "busy" merely because nothing could be measured.
    An unparseable `CPUPerc` field (Docker's own format, always
    formatted as `"12.34%"` today) is handled the same way.

    **Host-touching, so verified live rather than in the governed
    suite, per decision #9 (2026-08-29).** `resolve_cpu_active`
    itself is pure and fully covered; this class is the thin,
    untested shell around it, the same split
    `apply_resource_priority` draws around `cpus_equal`/
    `format_cpus`.
    """

    def __init__(
        self,
        container: str,
        threshold_percent: float,
        sustained_seconds: float,
    ) -> None:
        self._container = container
        self._threshold_percent = threshold_percent
        self._sustained_seconds = sustained_seconds
        self._state = CpuStreakState()

    def is_active(self) -> bool:
        active, self._state = resolve_cpu_active(
            usage_percent=self._read_cpu_percent(),
            threshold_percent=self._threshold_percent,
            sustained_seconds=self._sustained_seconds,
            now=time.monotonic(),
            state=self._state,
        )

        return active

    def _read_cpu_percent(self) -> float:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{json .}}",
                self._container,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return 0.0

        try:
            payload = json.loads(result.stdout.strip())
            return float(str(payload.get("CPUPerc", "0%")).rstrip("%"))
        except (json.JSONDecodeError, ValueError, AttributeError):
            return 0.0
