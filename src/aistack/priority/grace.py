from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraceState:
    """
    What the monitor remembers between two polls, and nothing more.

    `last_playing_at` is a `time.monotonic()` reading, never a wall
    clock — a system clock adjustment (NTP, DST, the owner setting
    the time by hand) must not manufacture or erase a grace period.
    `None` means "not currently within a grace window": either
    playback has never been seen, or the window already elapsed.
    """

    last_playing_at: float | None = None


def resolve_boosted(
    playing_now: bool,
    now: float,
    grace_seconds: float,
    state: GraceState,
) -> tuple[bool, GraceState]:
    """
    Whether the front-line boost should be active on this poll, and
    the state to carry into the next one.

    **Pure, and separate from the monitor loop on purpose** — same
    split as everywhere else in this feature. `now` and `state`
    arrive as plain values rather than being read from the clock in
    here, so a 60-second grace period is tested in a heartbeat
    instead of a test that actually waits 60 seconds.

    **A session playing always wins immediately.** There is no
    grace period on the way *up* — decision #1 already put
    detection on `/Sessions`, not a load heuristic, precisely so a
    quiet direct-play stream would not be missed; delaying the
    boost after it is already confirmed would undo that. Only the
    way *down*, from playing to not, waits.

    **Decision of 2026-09-03: 60 seconds.** Long enough to absorb a
    bathroom break or a phone call without radarr and qBittorrent
    being unbridled and rebridled minutes apart; short enough that
    closing Jellyfin for the night gives the background containers
    their machine back inside a minute, not after it.
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
