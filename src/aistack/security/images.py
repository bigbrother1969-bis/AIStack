"""
How old the images of the running containers are (ADR-0028 § 2, slice T2b).

Read-only, from `docker image inspect`. The age is the image's build
date, read locally: no registry is asked, so the assessment says what is
old, never that a newer image exists, and no data leaves the LAN. An image
built a year ago has gone a year without the maintainer's fixes, unless
the project is finished; the owner accepts those by container name
(`accepted: old_image`).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from datetime import datetime, timezone

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH, Finding
from aistack.security.hygiene import OLD_IMAGE, Container

CommandRunner = Callable[..., "subprocess.CompletedProcess[str]"]


def _date(text: str) -> datetime | None:
    # Docker writes nanoseconds ("2025-10-01T12:00:00.123456789Z"); Python reads microseconds.
    text = text.strip()
    if not text.endswith("Z"):
        return None

    body, _, fraction = text[:-1].partition(".")
    try:
        parsed = datetime.fromisoformat(f"{body}.{fraction[:6].ljust(6, '0')}" if fraction else body)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def parse_created(text: str) -> dict[str, datetime]:
    """`<id> <date>` lines to a map of image id to build date; a line that cannot be read is skipped."""

    found: dict[str, datetime] = {}
    for line in text.splitlines():
        identifier, _, stamp = line.strip().partition(" ")
        built = _date(stamp)
        if identifier and built is not None:
            found[identifier] = built
    return found


def read_created(identifiers: list[str], run_command: CommandRunner = subprocess.run) -> dict[str, datetime] | None:
    """The build date of each image; None when Docker cannot be asked."""

    if not identifiers:
        return {}

    try:
        result = run_command(
            ["docker", "image", "inspect", "--format", "{{.Id}} {{.Created}}", *identifiers],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    return parse_created(result.stdout) if result.returncode == 0 else None


def _listed(names: list[str], limit: int) -> tuple[str, ...]:
    return tuple(names) if len(names) <= limit else (*names[:limit], f"and {len(names) - limit} more")


def old_images(
    containers: list[Container],
    created: dict[str, datetime],
    now: datetime,
    definition: SecurityDefinition,
) -> list[tuple[Container, int]]:
    """The containers whose image is older than the limit and not accepted, oldest first, with its age in days."""

    found = [
        (item, (now - created[item.image_id]).days)
        for item in containers
        if item.image_id in created and item.name not in definition.accepted.get(OLD_IMAGE, ())
    ]
    return sorted(((item, days) for item, days in found if days > definition.max_image_age_days), key=lambda pair: -pair[1])


def assess_images(
    containers: list[Container] | None,
    created: dict[str, datetime] | None,
    now: datetime,
    definition: SecurityDefinition,
) -> list[Finding]:
    if not containers:
        return []

    if created is None:
        return [
            Finding(
                "images.unreadable",
                WATCH,
                "The images of the containers could not be inspected",
                unknown="How old the images are.",
            )
        ]

    findings: list[Finding] = []
    old = old_images(containers, created, now, definition)

    if old:
        findings.append(
            Finding(
                "images.old",
                WATCH,
                f"{len(old)} container(s) run an image built more than {definition.max_image_age_days} days ago",
                _listed([f"{item.name} ({item.image}): {days} days" for item, days in old], definition.max_listed),
                unknown="Whether a newer image exists; no registry is asked. Whether this project is still maintained.",
            )
        )

    accepted = [
        item.name
        for item in containers
        if item.name in definition.accepted.get(OLD_IMAGE, ())
        and item.image_id in created
        and (now - created[item.image_id]).days > definition.max_image_age_days
    ]
    if accepted:
        findings.append(
            Finding(
                "images.accepted",
                INFORMATION,
                f"{len(accepted)} old image(s) are accepted in security.yml",
                _listed(accepted, definition.max_listed),
                unknown="Whether each is still needed.",
            )
        )

    return findings
