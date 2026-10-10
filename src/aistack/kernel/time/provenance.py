from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Provenance:
    """
    Where a snapshot's content came from.

    `origin` identifies the component that produced it. `causality` is
    the identifier of the request or task that caused production, or
    `None` when nothing triggered it (e.g. a plain CLI run).
    """

    origin: str
    causality: str | None = None
