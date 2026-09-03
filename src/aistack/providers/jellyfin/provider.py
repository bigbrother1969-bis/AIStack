from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


class JellyfinProvider:
    """
    Observe what Jellyfin knows about who is playing what, right now.

    A provider observes and does not qualify — same rule as
    `SyncthingProvider`. `/Sessions` is returned exactly as the
    server answered it, one entry per connected client, whether or
    not anything is actually playing; deciding what that means —
    whether it counts as "someone is watching" — belongs to
    whatever composes this (`aistack.priority.playback`), not to
    the provider.

    **Unreachable is a state, not an error.** The daemon can be
    restarting, its key can have been rotated, the host can be
    unreachable — none of that is exceptional enough to raise. This
    returns `reachable: false` with the reason as a sentence, for
    the same reason `SyncthingProvider` does: a caller that decides
    to leave every background container at full throttle when it
    cannot ask is a caller that needs a state to read, not a
    traceback to catch.

    **The key is a value, never a lookup.** This class reads no
    environment and no file; the definition names where the key
    lives, the caller reads it and passes it here — GOV-P-001, the
    same handling as the Syncthing key.

    **The session shape was verified against the owner's real
    Jellyfin, 2026-09-03.** `collect()` returns the sessions
    unqualified precisely so that whatever the real shape turned
    out to be would be visible in full rather than filtered through
    a wrong assumption — the same caution the Syncthing `device_id`
    precedent earned (a documented shape that was still a literal
    placeholder string on first real contact). Two real payloads
    from the owner's own daemon confirmed `NowPlayingItem` and
    `PlayState.IsPaused` are exactly right; `aistack.priority.
    playback.has_active_playback`, which reads them, carries the
    same confirmation.
    """

    provider_id = "aistack.provider.jellyfin"
    provider_name = "Jellyfin Provider"

    def __init__(
        self,
        url: str,
        api_key: str,
        timeout: float = 5.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def collect(self) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "jellyfin": {
                "url": self.url,
                "reachable": False,
                "unreachable_reason": "",
                "sessions": [],
            },
        }

        state = observation["jellyfin"]

        if not self.api_key:
            state["unreachable_reason"] = (
                "no API key was provided, so Jellyfin was not asked"
            )
            return observation

        sessions, reason = self._get("/Sessions")

        if reason:
            state["unreachable_reason"] = reason
            return observation

        state["reachable"] = True
        state["sessions"] = sessions if isinstance(sessions, list) else []

        return observation

    def _get(self, path: str) -> tuple[Any, str]:
        """
        One call, and every failure turned into a sentence — same
        shape as `SyncthingProvider._get`. The key travels in the
        header (`X-Emby-Token`, the name Jellyfin documents for
        this), never in the query string, where it would land in
        the daemon's own access log.
        """

        request = urllib.request.Request(
            f"{self.url}{path}",
            headers={"X-Emby-Token": self.api_key},
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                return json.load(response), ""

        except TimeoutError:
            return [], self._timed_out()

        except urllib.error.HTTPError as error:
            return [], (
                f"Jellyfin refused {path} with status {error.code} "
                f"({error.reason})"
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return [], self._timed_out()

            return [], f"Jellyfin at {self.url} could not be reached: {error.reason}"

        except (ValueError, OSError) as error:
            return [], f"Jellyfin answered {path} with something unreadable: {error}"

    def _timed_out(self) -> str:
        return (
            f"Jellyfin at {self.url} did not answer within "
            f"{self.timeout} seconds"
        )
