from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


class SyncthingProvider:
    """Observe what Syncthing knows about one folder and one device.

    Data is passed through as the daemon reported it. `/rest/db/status`
    describes the folder on this server; `/rest/db/completion` describes
    how much of it has reached the device, which is a different question.

    Unreachable is a state (`reachable: false` plus a reason), not an
    exception. The API key is passed in by the caller; this class reads no
    environment or file. Missing fields are not defaulted to zero.
    """

    provider_id = "aistack.provider.syncthing"
    provider_name = "Syncthing Provider"

    def __init__(
        self,
        url: str,
        api_key: str,
        folder_id: str,
        device_id: str = "",
        timeout: float = 5.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.folder_id = folder_id
        self.device_id = device_id
        self.timeout = timeout

    def collect(self) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "syncthing": {
                "url": self.url,
                "folder_id": self.folder_id,
                "device_id": self.device_id,
                "reachable": False,
                "unreachable_reason": "",
                "folder": {},
                "device": {},
            },
        }

        state = observation["syncthing"]

        if not self.api_key:
            state["unreachable_reason"] = (
                "no API key was provided, so Syncthing was not asked"
            )
            return observation

        folder, reason = self._get(
            "/rest/db/status", {"folder": self.folder_id}
        )

        if reason:
            state["unreachable_reason"] = reason
            return observation

        state["reachable"] = True
        state["folder"] = folder

        if not self.device_id:
            return observation

        device, reason = self._get(
            "/rest/db/completion",
            {"folder": self.folder_id, "device": self.device_id},
        )

        if reason:
            # The folder status was read; only the device half is missing.
            state["device"] = {"unavailable_reason": reason}
            return observation

        state["device"] = device

        return observation

    def _get(
        self, path: str, parameters: dict[str, str]
    ) -> tuple[dict[str, Any], str]:
        """One GET; every failure becomes a reason sentence shown on screen.

        `HTTPError` covers a rejected key; `URLError` covers refused
        connections, DNS failures and timeouts.
        """

        query = urllib.parse.urlencode(parameters)

        request = urllib.request.Request(
            f"{self.url}{path}?{query}",
            headers={"X-API-Key": self.api_key},
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                return json.load(response), ""

        except TimeoutError:
            return {}, self._timed_out()

        except urllib.error.HTTPError as error:
            return {}, (
                f"Syncthing refused {path} with status {error.code} "
                f"({error.reason})"
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return {}, self._timed_out()

            return {}, f"Syncthing at {self.url} could not be reached: {error.reason}"

        except (ValueError, OSError) as error:
            return {}, f"Syncthing answered {path} with something unreadable: {error}"

    def _timed_out(self) -> str:
        """Reason for a timeout, distinct from a refused connection.

        A connect timeout arrives wrapped in `URLError`; a read timeout
        raises `TimeoutError` directly. Both are caught.
        """

        return (
            f"Syncthing at {self.url} did not answer within "
            f"{self.timeout} seconds"
        )
