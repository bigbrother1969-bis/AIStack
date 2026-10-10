from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


class JellyfinProvider:
    """Observe Jellyfin's current sessions (`/Sessions`).

    Sessions are returned as the server answered, one per connected
    client; `aistack.priority.playback` decides what counts as playing.
    Unreachable is a state (`reachable: false` plus a reason), not an
    exception. The API key is passed in by the caller; this class reads no
    environment or file.
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
        """One GET; every failure becomes a reason sentence.

        The key goes in the `X-Emby-Token` header, never the query string,
        where it would end up in Jellyfin's access log.
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
