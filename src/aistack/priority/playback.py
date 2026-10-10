from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def has_active_playback(sessions: Iterable[dict[str, Any]]) -> bool:
    """
    Whether any Jellyfin session is playing and not paused.

    A session is a connected client, not a viewer: only a session with
    `NowPlayingItem` is playing. A missing `PlayState.IsPaused` counts as
    playing, so a real watch never fails to trigger the priority.
    """

    return any(_is_playing(session) for session in sessions)


def _is_playing(session: dict[str, Any]) -> bool:

    if not session.get("NowPlayingItem"):
        return False

    play_state = session.get("PlayState") or {}

    return play_state.get("IsPaused", False) is not True
