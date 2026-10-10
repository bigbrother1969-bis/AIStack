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
    A historicised payload with its version, provenance and instant:
    what it is, as of when, from where.

    `content` is generic (`T`). Unlike `TemporalEvent`, a snapshot
    carries `observed_at` itself, because it is the record whose
    history filename is derived from that instant.
    """

    content: T
    version: VersionId
    provenance: Provenance
    observed_at: datetime
