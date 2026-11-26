from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


_USER_AGENT = "AIStack-BeszelProvider/1.0"
# A PocketBase record id: nothing else is put in a filter.
_IDENTIFIER = re.compile(r"[A-Za-z0-9]{1,40}")


class BeszelProvider:
    """Observe the systems Beszel's hub monitors.

    Each item in `systems` is the raw PocketBase record;
    `aistack.architecture.beszel_reading` interprets it. Two requests:
    email/password authentication returns a token, then the systems list
    is fetched with that token as the raw `Authorization` value (no
    `Bearer ` prefix).

    Unreachable is a state (`reachable: false` plus a reason naming the
    failed step), not an exception. Credentials are passed in by the
    caller; use a Beszel account with the `readonly` role. Every request
    sends an explicit `User-Agent`: Cloudflare rejects urllib's default one
    with a 403 (`error code: 1010`).
    """

    provider_id = "aistack.provider.beszel"
    provider_name = "Beszel Provider"

    def __init__(
        self,
        url: str,
        email: str,
        password: str,
        timeout: float = 5.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.email = email
        self.password = password
        self.timeout = timeout

    def collect(self, last_readings: bool = False) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "beszel": {
                "url": self.url,
                "reachable": False,
                "unreachable_reason": "",
                "systems": [],
            },
        }

        state = observation["beszel"]

        if not self.email or not self.password:
            state["unreachable_reason"] = (
                "no credentials were provided, so Beszel was not asked"
            )
            return observation

        token, reason = self._authenticate()

        if reason:
            state["unreachable_reason"] = reason
            return observation

        items, reason = self._get("/api/collections/systems/records", token)

        if reason:
            state["unreachable_reason"] = reason
            return observation

        state["reachable"] = True
        state["systems"] = items if isinstance(items, list) else []

        if last_readings:
            self._add_last_readings(state["systems"], token)

        return observation

    def _add_last_readings(self, systems: list[Any], token: str) -> None:
        """
        For each system Beszel calls down, when its last measure arrived (`last_reading`, from `system_stats`).

        The record's own `updated` is not that: it changes when a person edits the record. A failure here only
        leaves the key out; the observation is the same without it.
        """

        for item in systems:
            if not isinstance(item, dict) or item.get("status") != "down" or not _IDENTIFIER.fullmatch(str(item.get("id", ""))):
                continue

            query = urllib.parse.urlencode(
                {"filter": f"system='{item['id']}'", "sort": "-created", "perPage": 1, "fields": "created"}
            )
            found, reason = self._get(f"/api/collections/system_stats/records?{query}", token)

            if not reason and isinstance(found, list) and found and isinstance(found[0], dict) and isinstance(found[0].get("created"), str):
                item["last_reading"] = found[0]["created"]

    def _authenticate(self) -> tuple[str, str]:
        """`POST /api/collections/users/auth-with-password`; return the token,
        or an empty string and a reason."""

        body = json.dumps(
            {"identity": self.email, "password": self.password}
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.url}/api/collections/users/auth-with-password",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                answer = json.load(response)

        except TimeoutError:
            return "", self._timed_out()

        except urllib.error.HTTPError as error:
            return "", (
                f"Beszel refused authentication with status {error.code} "
                f"({error.reason})"
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return "", self._timed_out()

            return "", f"Beszel at {self.url} could not be reached: {error.reason}"

        except (ValueError, OSError) as error:
            return "", f"Beszel answered authentication with something unreadable: {error}"

        token = answer.get("token", "") if isinstance(answer, dict) else ""

        if not token:
            return "", "Beszel authenticated but returned no token"

        return token, ""

    def _get(self, path: str, token: str) -> tuple[Any, str]:
        """One GET; every failure becomes a reason sentence. Returns the
        `items` of the first page of PocketBase's list envelope."""

        request = urllib.request.Request(
            f"{self.url}{path}",
            headers={"Authorization": token, "User-Agent": _USER_AGENT},
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                answer = json.load(response)

        except TimeoutError:
            return [], self._timed_out()

        except urllib.error.HTTPError as error:
            return [], (
                f"Beszel refused {path} with status {error.code} "
                f"({error.reason})"
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return [], self._timed_out()

            return [], f"Beszel at {self.url} could not be reached: {error.reason}"

        except (ValueError, OSError) as error:
            return [], f"Beszel answered {path} with something unreadable: {error}"

        items = answer.get("items", []) if isinstance(answer, dict) else []

        return items, ""

    def _timed_out(self) -> str:
        return (
            f"Beszel at {self.url} did not answer within "
            f"{self.timeout} seconds"
        )


def collect_beszel(url: str, email: str, password: str, timeout: float = 5.0, last_readings: bool = False) -> dict[str, Any]:
    """Observe Beszel once. Callers outside the providers ask for the observation, they do not build the provider."""

    return BeszelProvider(url, email, password, timeout=timeout).collect(last_readings=last_readings)
