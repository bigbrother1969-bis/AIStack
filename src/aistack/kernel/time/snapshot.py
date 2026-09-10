from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from aistack.kernel.time.provenance import Provenance
from aistack.kernel.time.version import VersionId

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Snapshot(Generic[T]):
    """
    Governed snapshot contract — J3, Time Foundation
    (`claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`).

    **Names what `write_artifact_with_history` already produces as a
    side effect, and what `aistack.history.query.HistoricalObservation`
    already reads back, without either ever being a shared, reusable
    contract.** Before this patch, each historicised stream answered
    "what is this, as of when, from where" with its own ad hoc shape:
    `HistoricalObservation` (`stem`/`observed_at`/`path`, read-side
    only), `serialize_execution_trace`'s dict (no version, no
    provenance), `decision_history.serialize_decision`'s dict (an
    `observed_at` field redundant with the filename it is written
    under — the one inconsistency this plan's own research found
    between existing streams). `Snapshot` is the one shape all of
    them can produce instead.

    `content` is the payload being historicised — deliberately
    generic (`T`), since a `Snapshot[ExecutionTrace]` and a
    `Snapshot[ApplyReport]` have nothing in common beyond needing the
    same three facts about themselves.

    **`observed_at` is carried by the object here, unlike
    `TemporalEvent`.** A `TemporalEvent` describes something that
    happened at an instant some other record already states (the
    history filename); a `Snapshot` *is* the record — it is what
    gives that instant its filename in the first place, so it has to
    carry it, not defer to a file that does not exist yet at
    construction time.
    """

    content: T
    version: VersionId
    provenance: Provenance
    observed_at: datetime
