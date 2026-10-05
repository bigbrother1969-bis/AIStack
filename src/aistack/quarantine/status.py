"""
Where each quarantined item stands (`OPS-0012`): watched, used (an
alarm), or ready to be deleted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pathlib import Path

from aistack.contracts.quarantine_reading import READY, USED, WATCHED
from aistack.quarantine.hits import Hit, read_hits
from aistack.quarantine.register import (
    REGISTER,
    QuarantineEntry,
    entry_of_module,
    entry_of_path,
    load_register,
)
from aistack.quarantine.tripwire import HITS


@dataclass(frozen=True)
class EntryStatus:
    entry: QuarantineEntry
    state: str
    hits: tuple[Hit, ...]


def entry_hits(entries: tuple[QuarantineEntry, ...], hits: tuple[Hit, ...]) -> dict[str, tuple[Hit, ...]]:
    found: dict[str, list[Hit]] = {entry.id: [] for entry in entries}
    for hit in hits:
        entry = (
            entry_of_module(entries, hit.target)
            if hit.kind == "module"
            else entry_of_path(entries, hit.target)
        )
        if entry is not None:
            found[entry.id].append(hit)
    return {identifier: tuple(values) for identifier, values in found.items()}


def statuses(entries: tuple[QuarantineEntry, ...], hits: tuple[Hit, ...], today: date) -> tuple[EntryStatus, ...]:
    by_entry = entry_hits(entries, hits)
    result = []
    for entry in entries:
        used = by_entry[entry.id]
        if used:
            state = USED
        elif today >= entry.review_after:
            state = READY
        else:
            state = WATCHED
        result.append(EntryStatus(entry=entry, state=state, hits=used))
    return tuple(result)


def read_statuses(today: date, register: Path = REGISTER, hits: Path = HITS) -> tuple[EntryStatus, ...]:
    """The register and the recorded uses, read together."""

    return statuses(load_register(register), read_hits(hits), today)
