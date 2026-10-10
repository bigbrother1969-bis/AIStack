from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CpuStreakState:
    """
    What `resolve_cpu_active` keeps between two polls.

    `above_since` is a `time.monotonic()` reading; `None` means the last
    reading was below the threshold.
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
    Return whether this poll's CPU reading counts as active, and the state
    for the next poll.

    Debounces the way up only: usage must stay at or above
    `threshold_percent` for `sustained_seconds` before this returns True.
    One reading below the threshold resets the streak. The way down is
    smoothed by `resolve_boosted`. Pure: `now` and `state` are passed in.
    """

    if usage_percent >= threshold_percent:
        since = state.above_since if state.above_since is not None else now
        return (now - since) >= sustained_seconds, CpuStreakState(above_since=since)

    return False, CpuStreakState(above_since=None)


class CpuThresholdDetector:
    """
    Detect activity by a container's live CPU usage, sustained over time.

    Reads `docker stats --no-stream` and folds the reading through
    `resolve_cpu_active`. A failed call or an unparseable `CPUPerc` reads
    as 0 %, so a stopped or missing container never counts as busy.
    Not unit-tested: it calls Docker; `resolve_cpu_active` is.
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
