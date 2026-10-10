from __future__ import annotations

import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


_USER_AGENT = "AIStack-HttpProbeProvider/1.0"


class HttpProbeProvider:
    """Ask each configured HTTP endpoint for its status code.

    Observes only; the status code is reported as answered. Unreachable is
    a state, not an exception: any HTTP answer (including 4xx/5xx) is
    `reachable`, only no answer at all is not. No credentials are used.

    Every request sends an explicit `User-Agent`: Cloudflare rejects
    urllib's default one with a 403 (`error code: 1010`).
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
            # An error status is still an answer: reachable.
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
