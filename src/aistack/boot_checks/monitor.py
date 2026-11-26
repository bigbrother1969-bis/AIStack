"""
What Uptime Kuma says of its monitors, read through its API key (ADR-0032, slice B4b).

Uptime Kuma publishes `/metrics` for Prometheus: HTTP Basic, the username
ignored and the password an API key made in its own Settings. Each monitor that
runs has a `monitor_status` line (1 up, 0 down, 2 pending, 3 maintenance). A
monitor that is *paused* is not published at all, so a paused monitor and a
deleted one look alike: both are "missing" to a reference list.

Read-only: one GET. The key is never put in a message or a file, and neither is
the address; what comes out is monitor names and their status.
"""

from __future__ import annotations

import base64
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "AIStack-BootChecks/1.0"
UP, DOWN, WAITING, MAINTENANCE = 1, 0, 2, 3
_LINE = re.compile(r"^monitor_status\{(?P<labels>.*)\}\s+(?P<value>[0-9.eE+-]+)\s*$")
_NAME = re.compile(r'monitor_name="((?:[^"\\]|\\.)*)"')


@dataclass(frozen=True)
class MonitorReading:
    """The monitors Uptime Kuma publishes and their status, or why they could not be read."""

    reachable: bool
    reason: str = ""
    monitors: dict[str, int] = field(default_factory=dict)


def parse_metrics(text: str) -> dict[str, int]:
    """Monitor name -> status, from the Prometheus text; a line that is not a `monitor_status` one is not read."""

    found: dict[str, int] = {}

    for line in text.splitlines():
        match = _LINE.match(line.strip())

        if match is None:
            continue

        name = _NAME.search(match.group("labels"))

        if name is None:
            continue

        try:
            status = int(float(match.group("value")))
        except ValueError:
            continue

        found[name.group(1).replace('\\"', '"').replace("\\\\", "\\")] = status

    return found


def read_monitors(url: str, api_key: str, timeout: float = 20.0) -> MonitorReading:
    """One request to `<url>/metrics`; unreachable is a state with a reason, never an exception."""

    token = base64.b64encode(f":{api_key}".encode()).decode()
    request = urllib.request.Request(
        url.rstrip("/") + "/metrics", headers={"Authorization": f"Basic {token}", "User-Agent": USER_AGENT}
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310 - the owner's own address
            text = answer.read(4_000_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        why = "the API key was refused" if error.code in (401, 403) else f"Uptime Kuma answered {error.code}"

        return MonitorReading(False, why)
    except (urllib.error.URLError, OSError, ValueError) as error:
        return MonitorReading(False, f"Uptime Kuma did not answer ({type(error).__name__})")

    monitors = parse_metrics(text)

    if not monitors:
        return MonitorReading(False, "Uptime Kuma publishes no monitor (all paused, or not its metrics)")

    return MonitorReading(True, "", monitors)
