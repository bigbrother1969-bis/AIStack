from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraceState:
    """
    What the monitor keeps between two polls.

    `last_playing_at` is a `time.monotonic()` reading, so clock changes
    cannot create or erase a grace period. `None` means not within a
    grace window.
    """

    last_playing_at: float | None = None


def resolve_boosted(
    playing_now: bool,
    now: float,
    grace_seconds: float,
    state: GraceState,
) -> tuple[bool, GraceState]:
    """
    Return whether the boost is active on this poll, and the state for the
    next one.

    Activity boosts immediately; only the way down waits `grace_seconds`,
    so a short pause does not unboost and reboost the background containers.
    Pure: `now` and `state` are passed in.
    """

    if playing_now:
        return True, GraceState(last_playing_at=now)

    within_grace = (
        state.last_playing_at is not None
        and (now - state.last_playing_at) < grace_seconds
    )

    if within_grace:
        return True, state

    return False, GraceState(last_playing_at=None)
