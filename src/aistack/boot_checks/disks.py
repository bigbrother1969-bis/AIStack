"""
What Scrutiny says of the disks, read through its own API (ADR-0032, slice O1b).

Scrutiny keeps the SMART readings of the disks and publishes them without a key on the LAN:
`/api/summary` lists every disk it ever saw, by WWN, and `/api/device/<wwn>/details` gives the
attributes of one. Read-only: a few GET requests, no secret.

What is read, and what is not trusted:

- A disk is known by its **WWN**, never by `sda`: the same name can belong to two disks, one of
  them archived.
- A disk Scrutiny **archived** is no longer in the machine and is not judged.
- `smart_support` is not used: Scrutiny reports it false for disks whose readings it has.
  A disk is *not read* when its attributes are missing, not when that flag says so.
- Scrutiny's own `status` of a disk or of an attribute comes from failure statistics (more than
  10 % or 20 % of the disks with that value failed), not from a threshold the disk crossed.
  Only the **SMART failure** bit (value 1) is a failure; the rest is kept apart as a hint.
- A counter is read as it is now. Whether it grows is for the history to say, not for this reading.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

USER_AGENT = "AIStack-BootChecks/1.0"

# The ATA attributes that mean a real fault when their raw value is above zero: reallocated sectors (5),
# spin retries (10), reported uncorrectable errors (187), pending sectors (197), offline uncorrectable (198).
CRITICAL_ATTRIBUTES = (5, 10, 187, 197, 198)

# The Scrutiny status bits: 1 is a SMART failure; 2 and 4 are warnings from failure statistics.
SMART_FAILED = 1
MAX_DISKS = 64


@dataclass(frozen=True)
class Disk:
    """One disk as Scrutiny knows it. `attributes_read` is false when its details did not come."""

    wwn: str
    label: str
    archived: bool
    hours: int | None = None
    collected_at: datetime | None = None
    failed_smart: bool = False
    worn: tuple[int, ...] = ()
    statistical: bool = False
    attributes_read: bool = False


@dataclass(frozen=True)
class DiskReading:
    """The disks Scrutiny publishes, or why they could not be read."""

    reachable: bool
    reason: str = ""
    disks: tuple[Disk, ...] = field(default_factory=tuple)


def _number(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return int(value)


def _moment(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    try:
        found = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


def _label(device: dict[str, Any]) -> str:
    """The model and the end of the serial number: two disks of one model stay apart, the serial is not shown whole."""

    model = " ".join(str(device.get("model_name") or "disk").split())[:40]
    serial = "".join(character for character in str(device.get("serial_number") or "") if character.isalnum())

    return f"{model} …{serial[-4:]}" if serial else model


def parse_details(details: Any) -> tuple[bool, tuple[int, ...]] | None:
    """(a SMART attribute failed, the critical attributes above zero), or `None` when the attributes are not there."""

    if not isinstance(details, dict):
        return None

    results = details.get("smart_results")

    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return None

    attributes = results[0].get("attrs")

    if not isinstance(attributes, dict) or not attributes:
        return None

    failed = False
    worn: list[int] = []

    for key, attribute in attributes.items():
        if not isinstance(attribute, dict):
            continue

        status = _number(attribute.get("status")) or 0

        if status & SMART_FAILED:
            failed = True

        try:
            number = int(key)
        except (TypeError, ValueError):
            continue

        if number in CRITICAL_ATTRIBUTES and (_number(attribute.get("raw_value")) or 0) > 0:
            worn.append(number)

    return failed, tuple(sorted(worn))


def parse_summary(summary: Any) -> list[tuple[str, dict[str, Any]]]:
    """The (WWN, entry) pairs of `/api/summary`; anything that is not that shape is not read."""

    data = summary.get("data") if isinstance(summary, dict) else None

    if not isinstance(data, dict):
        return []

    entries = data.get("summary")

    if not isinstance(entries, dict):
        return []

    return [(str(wwn), entry) for wwn, entry in entries.items() if isinstance(entry, dict) and isinstance(entry.get("device"), dict)][:MAX_DISKS]


def disk_of(wwn: str, entry: dict[str, Any], details: Any) -> Disk:
    device = entry["device"]
    found = entry.get("smart")
    smart: dict[str, Any] = found if isinstance(found, dict) else {}
    status = _number(device.get("device_status")) or 0
    read = parse_details(details)
    failed, worn = read if read is not None else (False, ())

    return Disk(
        wwn=wwn,
        label=_label(device),
        archived=bool(device.get("archived")),
        hours=_number(smart.get("power_on_hours")),
        collected_at=_moment(smart.get("collector_date")),
        failed_smart=bool(status & SMART_FAILED) or failed,
        worn=worn,
        statistical=bool(status & ~SMART_FAILED),
        attributes_read=read is not None,
    )


def _get(url: str, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310 - the owner's own address
        return json.loads(answer.read(4_000_000).decode("utf-8", errors="replace"))


def read_disks(url: str, timeout: float = 10.0) -> DiskReading:
    """The summary, then the details of each disk that is still in the machine; unreachable is a state with a reason."""

    base = url.rstrip("/")

    try:
        pairs = parse_summary(_get(base + "/api/summary", timeout))
    except urllib.error.HTTPError as error:
        return DiskReading(False, f"Scrutiny answered {error.code}")
    except (urllib.error.URLError, OSError, ValueError) as error:
        return DiskReading(False, f"Scrutiny did not answer ({type(error).__name__})")

    disks: list[Disk] = []

    for wwn, entry in pairs:
        details: Any = None

        if not entry["device"].get("archived"):
            try:
                details = _get(f"{base}/api/device/{urllib.parse.quote(wwn, safe='')}/details", timeout).get("data")
            except (urllib.error.URLError, OSError, ValueError, AttributeError):
                details = None

        disks.append(disk_of(wwn, entry, details))

    return DiskReading(True, "", tuple(disks))
