from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def has_active_playback(sessions: Iterable[dict[str, Any]]) -> bool:
    """
    Whether any Jellyfin session designates a real, unpaused watch.

    Pure, and separate from `JellyfinProvider` on purpose — the
    provider observes and does not qualify (its own docstring says
    so), so deciding what a session *means* belongs here, the same
    split `resolve_subtrees`/`assess_capacity` draw for the
    Selection UI.

    A session is a connected client, not a person watching:
    `/Sessions` lists every device signed in, most of them idle
    most of the time. Only a session carrying `NowPlayingItem` is
    playing anything at all, and only when `PlayState.IsPaused` is
    not `True` is it still drawing on the machine rather than
    sitting frozen on a paused frame.

    **`IsPaused` absent counts as playing, not as paused.** A
    session already mid-playback with a play state Jellyfin did not
    bother to repeat in full is still playing; treating an absent
    field as "paused" would let a real, ongoing watch fail to
    trigger the priority it exists to protect, and this project's
    two most‑costly defects so far (the `Music-Android` folder
    left half-written, seven weeks of a phone silently behind) were
    both a screen or a generator staying quiet when it should not
    have. `NowPlayingItem` absent is read the other way — nothing
    playing is nothing to protect — because there the missing field
    *is* the fact.

    **Verified against the owner's real Jellyfin, 2026-09-03.**
    `NowPlayingItem` and `PlayState.IsPaused` were Jellyfin's
    documented session shape when this was written, and this
    codebase already had one instance of a documented shape not
    matching the field on first live contact (Syncthing's
    `device_id`) — so this was not trusted until it was run against
    two real payloads from the owner's own daemon: an idle session
    (no `NowPlayingItem`) and one playing *Le Calendrier*
    (`NowPlayingItem` present, `PlayState.IsPaused: false`). Both
    field names matched exactly; no correction was needed.
    """

    return any(_is_playing(session) for session in sessions)


def _is_playing(session: dict[str, Any]) -> bool:

    if not session.get("NowPlayingItem"):
        return False

    play_state = session.get("PlayState") or {}

    return play_state.get("IsPaused", False) is not True
