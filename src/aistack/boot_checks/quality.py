"""
How well AIStack itself is doing its part of the start-up checks (ADR-0032, slice O10).

The checks judge the host; this judges the checks: does the engine answer, how long does it take, which anomalies are
left without words, how long a pass lasts. Nothing new is written for it: it reads the journal of the engine's calls
(`ai-calls.jsonl`, which already keeps who asked, the engine, the duration and whether it answered, never a question
or an answer) and the last verdict. "Not measured is not zero": with fewer than `min_calls` calls in the window it
says it cannot judge, instead of showing a rate made of two calls. It is shown on the page, never in a verdict: how
the engine is doing never turns the start of the host to watch.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Protocol

CALLER = "boot_checks"
OPERATIONS = ("explain", "choose")


class Call(Protocol):
    """What is read of a call of the journal of the engine (read-only, so the journal's frozen records fit)."""

    @property
    def at(self) -> str: ...

    @property
    def caller(self) -> str: ...

    @property
    def operation(self) -> str: ...

    @property
    def reachable(self) -> bool: ...

    @property
    def seconds(self) -> float: ...


@dataclass(frozen=True)
class Quality:
    """What the engine did for the checks in the window: calls, answers, how long it took."""

    calls: int = 0
    answered: int = 0
    median: float = 0.0
    slowest: float = 0.0
    days: int = 7
    min_calls: int = 5

    @property
    def enough(self) -> bool:
        return self.calls >= self.min_calls


def read_quality(calls: Iterable[Call], now: datetime, days: int, min_calls: int) -> Quality:
    """The calls of `boot_checks` in the last `days` days; a call whose date cannot be read is left out, not guessed."""

    since = now - timedelta(days=days)
    seconds: list[float] = []
    answered = 0

    for call in calls:
        if call.caller != CALLER or call.operation not in OPERATIONS:
            continue

        try:
            when = datetime.fromisoformat(call.at)
        except ValueError:
            continue

        when = when if when.tzinfo is not None else when.replace(tzinfo=timezone.utc)

        if when < since:
            continue

        seconds.append(call.seconds)
        answered += 1 if call.reachable else 0

    if not seconds:
        return Quality(days=days, min_calls=min_calls)

    return Quality(len(seconds), answered, round(median(seconds), 1), round(max(seconds), 1), days, min_calls)


def unexplained(explanations: Iterable[object]) -> int:
    """Anomalies asked of the engine and left without words (a marker: an empty text)."""

    return sum(1 for item in explanations if not getattr(item, "text", "x"))
