"""
The question page's logic, free of the web (`portal.chat`, ADR-0029 § 12).

A person asks in their own words; AIStack chooses the engine by `ai_policy.yml` and says which and why.
The class of `portal.chat` is `internal_only` as shipped: the question stays on the machines until the
owner sets `external_allowed` in `ai_policy.yml`. Nothing typed is written anywhere: the journal of calls
holds the engine, the reason and the time, never a word of the question or of the answer.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from aistack.ai_runtime.call_journal import PORTAL_CHAT
from aistack.ai_runtime.policy import current_policy
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.troubleshooting import guide

KEPT_SECONDS = 1800
OPERATION = "ask"
_CHOSE = re.compile(r"chose ([^:;]+): ([^;]*)")


@dataclass(frozen=True)
class Destination:
    """Where the next question goes, from the declarations alone: asks nothing."""

    outside: bool
    engine: str


def destination() -> Destination:
    """The first engine the policy would ask: an outside one (named) or the machines' own."""

    definition = load_ai_runtime_yaml(guide.AI_RUNTIME)
    _, steps, _ = guide._plan_for(current_policy(), PORTAL_CHAT, OPERATION, definition)

    for step in steps:
        return Destination(step.outside, step.engine)

    return Destination(False, "")


@dataclass(frozen=True)
class Decision:
    """What the route says in simple words: the engine that answered and the reason given for it."""

    engine: str
    why: str


def decision_of(answer: AIRuntimeAnswer) -> Decision:
    """The engine that answered and why; the route is declarations only, never content."""

    found = _CHOSE.search(answer.route)
    engine = answer.model.split(" (", 1)[0].strip()

    return Decision(engine, found.group(2).strip() if found else "")


@dataclass
class Exchange:
    """One person's current question and its answer, in memory only."""

    question: str
    at: float
    answer: AIRuntimeAnswer | None = None
    failed: bool = False

    @property
    def pending(self) -> bool:
        return self.answer is None and not self.failed


@dataclass
class Exchanges:
    """The exchanges per person: one each, forgotten after half an hour and at each restart."""

    clock: Any = time.time
    _items: dict[str, Exchange] = field(default_factory=dict)

    def start(self, person: str, question: str) -> Exchange | None:
        """Begin a question; `None` when this person's previous one is still being answered."""

        current = self.of(person)

        if current is not None and current.pending:
            return None

        item = Exchange(question, float(self.clock()))
        self._items[person] = item
        return item

    def of(self, person: str) -> Exchange | None:
        item = self._items.get(person)

        if item is not None and float(self.clock()) - item.at > KEPT_SECONDS and not item.pending:
            del self._items[person]
            return None

        return item

    def forget(self, person: str) -> None:
        item = self._items.get(person)

        if item is not None and not item.pending:
            del self._items[person]
