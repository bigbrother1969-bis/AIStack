from __future__ import annotations

from datetime import datetime

from aistack.contracts.runtime_observation import (
    LogEntry,
    RuntimeObservation,
)


def split_timestamp(line: str) -> tuple[datetime | None, str]:
    """Split off the prefix `docker logs --timestamps` adds.

    Docker writes nanoseconds, which `datetime` cannot hold, so the
    fraction is truncated to microseconds. A line whose prefix does not
    parse is returned whole with no timestamp.
    """

    head, separator, tail = line.partition(" ")

    if not separator:
        return None, line

    candidate = head

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    if "." in candidate:
        seconds, _, fraction = candidate.partition(".")
        digits = fraction[:6]
        offset = fraction[len(digits) :].lstrip("0123456789")
        candidate = f"{seconds}.{digits}{offset}"

    try:
        return datetime.fromisoformat(candidate), tail
    except ValueError:
        return None, line


def normalize_log_evidence(
    raw: str,
    *,
    subject: str,
    provider: str,
    state: str,
    depth: int,
    collected_at: datetime,
) -> RuntimeObservation:
    """Turn a container's log output into a `RuntimeObservation` with one
    identified entry per line (`ADR-0008`, evidence normalization), so a
    finding can cite a line.

    The Docker timestamp prefix goes to its own field, so signatures never
    match it. Lines are otherwise kept verbatim. `offset` counts back from
    the newest line (0 = last printed). Empty output yields an observation
    with no entries, distinct from no observation.
    """

    lines = raw.split("\n")

    if lines and lines[-1] == "":
        # Drop the empty element after the final newline.
        lines.pop()

    last = len(lines) - 1

    entries = []

    for index, line in enumerate(lines):
        timestamp, text = split_timestamp(line)
        entries.append(
            LogEntry(
                offset=last - index,
                text=text,
                timestamp=timestamp,
            )
        )

    return RuntimeObservation(
        subject=subject,
        provider=provider,
        state=state,
        collected_at=collected_at,
        depth=depth,
        entries=tuple(entries),
    )
