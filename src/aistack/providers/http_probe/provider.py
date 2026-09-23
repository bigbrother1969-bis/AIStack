from __future__ import annotations

import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


_USER_AGENT = "AIStack-HttpProbeProvider/1.0"


class HttpProbeProvider:
    """
    Ask each configured HTTP endpoint for its status code, right now.

    `claude/PLAN-J11-CONSOLE-2026-09-11.md` §11.9.1, first of the
    three gaps named 2026-09-13, scoped and built 2026-09-23. A
    provider observes and does not qualify — same rule as
    `BeszelProvider`/`JellyfinProvider`/`SyncthingProvider`. The
    status code travels exactly as the server answered it; deciding
    what a 404 or a 500 means for the homelab is not this class's
    job.

    **"Injoignable" is a state, not an exception** — same reasoning
    every other network provider in this project already applies: a
    timeout, a DNS failure, a connection refused are all ordinary for
    a homelab-sized fleet of ~46 endpoints, not exceptional. An HTTP
    error status (4xx/5xx) is different from being unreachable: the
    server answered, so `reachable` is `True` and `status_code`
    carries whatever it said — only a request that never got an
    answer at all sets `reachable` to `False`.

    **No credentials.** These are the same public URLs already
    declared in this project (`service_categorization.yml`'s own
    `href` fields, `cmdb_probe_targets.yml` here) — unlike
    `BeszelProvider`/`JellyfinProvider`/`SyncthingProvider` there is
    nothing to authenticate, so `collect()` never reads `environ`.

    **An explicit `User-Agent` on every request** — the same fix
    `BeszelProvider` needed 2026-09-12, for the identical reason: most
    of these targets are `*.persiaut-family.fr` names fronted by the
    same Cloudflare, which refuses `urllib.request`'s own default
    signature with a bare 403 (`error code: 1010`). Applied here from
    the start rather than rediscovered against the real targets.
    """

    provider_id = "aistack.provider.http_probe"
    provider_name = "HTTP Probe Provider"

    def __init__(
        self,
        targets: tuple[tuple[str, str], ...],
        timeout: float = 5.0,
    ) -> None:
        self.targets = targets
        self.timeout = timeout

    def collect(self) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "http_probe": {
                "targets": [self._probe(name, url) for name, url in self.targets],
            },
        }

        return observation

    def _probe(self, name: str, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return self._reachable(name, url, response.status)

        except TimeoutError:
            return self._unreachable(name, url, self._timed_out(url))

        except urllib.error.HTTPError as error:
            # The server answered — with an error status, but it
            # answered. Reachable, same as a 2xx.
            return self._reachable(name, url, error.code)

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return self._unreachable(name, url, self._timed_out(url))

            return self._unreachable(
                name, url, f"{url} could not be reached: {error.reason}"
            )

        except (ValueError, OSError) as error:
            return self._unreachable(
                name, url, f"{url} answered with something unreadable: {error}"
            )

    def _reachable(self, name: str, url: str, status_code: int) -> dict[str, Any]:
        return {
            "name": name,
            "url": url,
            "reachable": True,
            "status_code": status_code,
            "unreachable_reason": "",
        }

    def _unreachable(self, name: str, url: str, reason: str) -> dict[str, Any]:
        return {
            "name": name,
            "url": url,
            "reachable": False,
            "status_code": None,
            "unreachable_reason": reason,
        }

    def _timed_out(self, url: str) -> str:
        return f"{url} did not answer within {self.timeout} seconds"
