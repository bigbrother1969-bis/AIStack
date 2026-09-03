from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


class SyncthingProvider:
    """
    Observe what Syncthing knows about one folder and one device.

    A provider observes and does not qualify. Everything here is
    passed through as the daemon reported it; deciding what a
    given state means for the screen belongs to whatever composes
    this with the selection.

    **Two questions, and the second is the one the screen was
    missing.** `/rest/db/status` describes the folder *on this
    server* — its state, what it holds, what it still needs.
    `/rest/db/completion` describes how much of it has reached the
    named device. Until 2026-09-03 the Selection UI asked only the
    first and labelled the answer as progress toward the phone.
    On 2026-08-29 that folder read `idle` with nothing pending
    while 159 selected artists had never been materialised at all:
    the number was right, the word above it was wrong, and the
    screen had shown it for seven weeks.

    **Unreachable is a state, not an error.** The phone answers
    only through a tunnel, and Android runs one VPN at a time, so
    its address changes and its absence is ordinary — measured
    2026-08-29. The daemon itself can be down, restarting, or
    behind a key that has been rotated. None of that is
    exceptional enough to raise: this returns `reachable: false`
    with the reason as a sentence, and the surface says so plainly
    instead of showing a stack trace or, worse, a stale figure.

    **The key is a value, never a lookup.** This class reads no
    environment and no file. The definition names where the key
    lives; the surface reads it and passes it here. So this is
    testable against a real HTTP server, and no secret can reach a
    governed artifact through it.

    **What is absent is absent.** Fields the daemon did not return
    are not defaulted to zero — a folder that answers without
    `needBytes` and a folder with nothing left to transfer are
    different facts, and only one of them is good news.
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
            # The daemon answered once and not twice. That is not
            # unreachable — what was read stays read, and the
            # missing half says why it is missing.
            state["device"] = {"unavailable_reason": reason}
            return observation

        state["device"] = device

        return observation

    def _get(
        self, path: str, parameters: dict[str, str]
    ) -> tuple[dict[str, Any], str]:
        """
        One call, and every failure turned into a sentence.

        The sentence is what a human reads on the screen when the
        phone is off or the key has been rotated, so it names what
        was tried. `URLError` covers a refused connection, a DNS
        failure and a timeout; `HTTPError` covers a rejected key,
        which is the one that looks like a network problem and is
        not.
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
        """
        A timeout reads differently from a refused connection.

        The screen is rendered on request: a daemon that hangs
        would hang the page, and the two failures lead to
        different actions — one is a daemon that is not there, the
        other one that is there and struggling.

        Both spellings are caught. A connection that times out
        arrives wrapped in `URLError`; a read that times out after
        the connection succeeded raises `TimeoutError` directly.
        Found by pointing the provider at a deliberately slow
        server on 2026-09-03 rather than by reading the standard
        library.
        """

        return (
            f"Syncthing at {self.url} did not answer within "
            f"{self.timeout} seconds"
        )
