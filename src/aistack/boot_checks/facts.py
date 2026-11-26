"""
The facts a host wrote about its start, read (ADR-0032, slice B1).

A small root unit on the host (`aistack-boot-facts`) writes
`boot-facts.json`: when the host started, the failed units, the mounted
file systems, the containers with their state and health, the rules of
`DOCKER-USER`, the KVM modules, how the previous run ended, the UPS and the
HTTP status of the declared probes. This module reads the file and says
what it holds; it judges nothing (that is slice B2) and it never takes a
source that failed, or a file that is old, for a healthy host.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FACTS = "boot-facts.json"
# The unit runs every five minutes; three missed runs make the file old.
MAX_AGE = timedelta(minutes=20)
# A host that may be off (ADR-0020): the same reason as the other snapshots.
REMOTE_MAX_AGE = timedelta(hours=25)
REMOTE_DIRECTORY = "boot"


@dataclass(frozen=True)
class Container:
    name: str
    state: str
    health: str


@dataclass(frozen=True)
class BootFacts:
    """
    What the host said. A field is `None` when its source did not answer
    (its reason is in `sources`), which is not the same as an empty list.
    """

    collected_at: datetime
    booted_at: datetime | None
    uptime_seconds: int | None
    boot_id: str
    failed_units: tuple[str, ...] | None
    mounts: tuple[str, ...] | None
    containers: tuple[Container, ...] | None
    docker_user_rules: int | None
    kvm_modules: bool | None
    previous_boot_clean: bool | None
    ups: str | None
    probes: dict[str, int] | None
    sources: dict[str, str] = field(default_factory=dict)


def _strings(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None

    return tuple(item for item in value if isinstance(item, str))


def _containers(value: Any) -> tuple[Container, ...] | None:
    if not isinstance(value, list):
        return None

    return tuple(
        Container(str(item["name"]), str(item.get("state", "")), str(item.get("health", "none")))
        for item in value
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _flag(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _instant(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_facts(text: str) -> BootFacts | None:
    """The facts in a file's text, or `None` when it is not a facts file."""

    try:
        raw = json.loads(text)
        collected = _instant(raw["collected_at"])
    except (ValueError, KeyError, TypeError):
        return None

    if collected is None or not isinstance(raw, dict):
        return None

    section = raw.get("boot")
    boot: dict[str, Any] = section if isinstance(section, dict) else {}
    probes = raw.get("probes")
    sources = raw.get("sources")

    return BootFacts(
        collected_at=collected,
        booted_at=_instant(boot.get("booted_at")) if boot.get("booted_at") else None,
        uptime_seconds=_count(boot.get("uptime_seconds")),
        boot_id=str(boot.get("boot_id", "")),
        failed_units=_strings(raw.get("failed_units")),
        mounts=_strings(raw.get("mounts")),
        containers=_containers(raw.get("containers")),
        docker_user_rules=_count(raw.get("docker_user_rules")),
        kvm_modules=_flag(raw.get("kvm_modules")),
        previous_boot_clean=_flag(raw.get("previous_boot_clean")),
        ups=raw["ups"] if isinstance(raw.get("ups"), str) else None,
        probes={str(k): v for k, v in probes.items() if isinstance(v, int)} if isinstance(probes, dict) else None,
        sources={str(k): str(v) for k, v in sources.items()} if isinstance(sources, dict) else {},
    )


def read_facts_file(directory: Path, now: datetime, max_age: timedelta = MAX_AGE) -> tuple[BootFacts | None, str]:
    """The facts a host unit wrote, and a sentence saying why there are none (empty when fresh)."""

    try:
        text = (directory / FACTS).read_text(encoding="utf-8")
    except OSError:
        return None, "no boot facts yet: install the host unit aistack-boot-facts"

    facts = parse_facts(text)

    if facts is None:
        return None, f"{FACTS} is not readable"

    if now - facts.collected_at > max_age:
        return None, f"{FACTS} is old ({facts.collected_at.isoformat(timespec='minutes')}): is the host unit still running?"

    return facts, ""
