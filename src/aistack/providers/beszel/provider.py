from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


class BeszelProvider:
    """
    Observe what Beszel's own hub knows about the systems it
    monitors, right now.

    A provider observes and does not qualify — same rule as
    `JellyfinProvider`/`SyncthingProvider`. Each item in `systems`
    travels exactly as Beszel's REST API answered it (a PocketBase
    `systems` collection record, `info` sub-object abbreviated keys
    included) — deciding what those abbreviations mean and turning
    them into something a page can display belongs to
    `aistack.architecture.beszel_reading.build_beszel_readings`, not
    to this class.

    **Two requests, not one.** Beszel's hub is PocketBase underneath
    (`beszel.dev/guide/rest-api`), and PocketBase authenticates a
    regular user with email+password against
    `/api/collections/users/auth-with-password`, returning a token —
    there is no static API key to hand this class the way
    `JellyfinProvider`/`SyncthingProvider` take one. The token from
    step one is then sent as the literal `Authorization` header value
    on step two (`/api/collections/systems/records`) — verified
    2026-09-12 against the owner's real hub that PocketBase here wants
    the raw token, not a `Bearer `-prefixed one; several PocketBase
    versions differ on this, so this is not assumed from the generic
    docs, it is what the owner's own `curl` against the real hub
    proved.

    **Unreachable is a state, not an error** — same reasoning as the
    other two network providers: a wrong password, a hub restarting,
    a expired/rotated credential are all ordinary, not exceptional.
    Both requests report their own failure into the same
    `unreachable_reason` sentence, naming which step failed.

    **The credentials are values, never a lookup.** This class reads
    no environment and no file; `infrastructure_topology.yml`'s
    `beszel:` block names which env vars hold them
    (`email_env`/`password_env`), and the caller
    (`aistack.cli.architecture_render`) reads those and passes the
    actual values here — `GOV-P-001`, the same handling as the
    Jellyfin/Syncthing keys.

    **Read-only by the account itself, not by this code.** The
    dedicated `aistack-readonly@persiaut-family.fr` Beszel account
    (role `readonly`, 2026-09-12) is what keeps this provider from
    being able to write anything, whatever it were asked to do —
    this class only ever calls the two `GET`/auth endpoints above.
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

    def collect(self) -> dict[str, Any]:
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

        return observation

    def _authenticate(self) -> tuple[str, str]:
        """
        `POST /api/collections/users/auth-with-password`, the generic
        PocketBase auth endpoint Beszel's own docs point at via the
        SDK-level `pb.collection('users').authWithPassword(...)`.

        Returns the token, or an empty string and a reason.
        """

        body = json.dumps(
            {"identity": self.email, "password": self.password}
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.url}/api/collections/users/auth-with-password",
            data=body,
            headers={"Content-Type": "application/json"},
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
        """
        One call, and every failure turned into a sentence — same
        shape as `JellyfinProvider._get`/`SyncthingProvider._get`.
        Beszel's own paginated list envelope (`{"items": [...], ...}`)
        is unwrapped to just `items` here — the caller wants the
        systems, not the pagination metadata this hub never needs
        more than one page of for a homelab-sized fleet.
        """

        request = urllib.request.Request(
            f"{self.url}{path}",
            headers={"Authorization": token},
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
