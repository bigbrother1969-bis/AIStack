"""
What the page *Moteurs IA* shows (`ADR-0029` § 8): the engines declared and what was last seen of
each, the policy, the counts by caller, kind and engine, and the why of the latest choices.

A reading over three things the owner already has: the declarations (`ai_runtime.yml`,
`ai_policy.yml`), the keys present in the environment, and the journal of AI calls. It asks no
engine, writes nothing and never shows a key or a word of any question: the journal holds none.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from aistack.ai_runtime.call_journal import Call
from aistack.ai_runtime.definition import AIRuntimeDefinition
from aistack.ai_runtime.policy import EXTERNAL, AIPolicy, Preference

# Outside engines, in the order they are asked by default, and what a page calls each.
HOSTED = (("gemini", "Gemini"), ("openai", "ChatGPT"), ("anthropic", "Claude"))

# Engine states (a catalog key each).
READY = "ready"
NO_KEY = "no_key"
NOT_DECLARED = "not_declared"


@dataclass(frozen=True)
class EngineRow:
    key: str  # `gemini`, `openai`, `anthropic`, or the label or model of a local engine
    label: str
    model: str
    where: str  # host:port of a local engine; empty for an outside one
    outside: bool
    state: str
    last_answered: str = ""  # when it last answered, from the journal
    last_seconds: float = 0.0
    last_silent_at: str = ""  # when it was last asked and said nothing
    last_silent_why: str = ""


@dataclass(frozen=True)
class Tally:
    calls: int = 0
    outside: int = 0  # the question went to an outside engine
    unanswered: int = 0  # nothing answered
    seconds: float = 0.0

    @property
    def average(self) -> float:
        return round(self.seconds / self.calls, 1) if self.calls else 0.0

    def counting(self, call: Call) -> "Tally":
        return Tally(
            self.calls + 1,
            self.outside + (1 if call.reached_external else 0),
            self.unanswered + (0 if call.reachable else 1),
            self.seconds + call.seconds,
        )


@dataclass(frozen=True)
class EnginesView:
    engines: tuple[EngineRow, ...]
    callers: tuple[tuple[str, str], ...]  # caller, class
    kinds: tuple[tuple[str, str], ...]  # `operation` or `caller.operation`, kind
    table: tuple[tuple[str, tuple[Preference, ...]], ...]  # kind, engines best first
    total: Tally
    by_caller: tuple[tuple[str, Tally], ...]
    by_kind: tuple[tuple[str, Tally], ...]
    by_engine: tuple[tuple[str, Tally], ...]
    with_fallback: int  # calls where an engine was asked first and said nothing
    recent: tuple[Call, ...]


def answerer(call: Call) -> str:
    """The engine that gave the answer: what `answered_by` says before the parenthesis that names the ones that stayed silent."""

    return call.answered_by.split(" (", 1)[0].strip() or "—"


_SILENT = re.compile(r"([A-Za-z0-9_.:\-]+) \(([^)]*)\)")


def silent_of(route: str) -> tuple[tuple[str, str], ...]:
    """The engines a route says were asked and stayed silent, with what they said (cut short in the journal)."""

    for part in route.split("; "):
        if part.startswith("silent: "):
            return tuple((name, why) for name, why in _SILENT.findall(part[len("silent: "):]))

    return ()


def _is_local(model: str, label: str) -> Callable[[str], bool]:
    return lambda who: who in (model, label) or model in who


def _is_hosted(key: str) -> Callable[[str], bool]:
    return lambda who: who.startswith(f"{key}:")


def _tally(calls: Iterable[Call], key: Callable[[Call], str]) -> tuple[tuple[str, Tally], ...]:
    found: dict[str, Tally] = {}

    for call in calls:
        label = key(call) or "—"
        found[label] = found.get(label, Tally()).counting(call)

    return tuple(sorted(found.items(), key=lambda item: (-item[1].calls, item[0])))


def _last_seen(calls: tuple[Call, ...], matches: Callable[[str], bool], silent_name: str) -> tuple[str, float, str, str]:
    """From the newest call: when the engine last answered, how long it took, and when and why it last stayed silent."""

    answered_at, seconds, silent_at, silent_why = "", 0.0, "", ""

    for call in calls:  # newest first
        if not answered_at and call.reachable and matches(answerer(call)):
            answered_at, seconds = call.at, call.seconds

        if not silent_at:
            for name, why in silent_of(call.route):
                if name == silent_name:
                    silent_at, silent_why = call.at, why
                    break

        if answered_at and silent_at:
            break

    return answered_at, seconds, silent_at, silent_why


def build(
    policy: AIPolicy,
    definition: AIRuntimeDefinition,
    keys_set: Iterable[str],
    calls: tuple[Call, ...],
    shown: int = 30,
) -> EnginesView:
    """
    The view, from the policy, the declared engines, the outside engines whose key is set (`keys_set`,
    names only) and the journal (`calls`, newest first).
    """

    keys = set(keys_set)
    declared = {"gemini": definition.gemini, "openai": definition.openai, "anthropic": definition.anthropic}
    rows: list[EngineRow] = []

    for local in definition.local_engines():
        label = local.label or local.model
        last = _last_seen(calls, _is_local(local.model, label), label)
        rows.append(
            EngineRow(
                key=label,
                label=label,
                model=local.model,
                where=f"{local.host}:{local.port}",
                outside=policy.kind_of_host(local.host) == EXTERNAL,
                state=READY,
                last_answered=last[0],
                last_seconds=last[1],
                last_silent_at=last[2],
                last_silent_why=last[3],
            )
        )

    for key, label in HOSTED:
        one = declared[key]
        state = NOT_DECLARED if one is None else (READY if key in keys else NO_KEY)
        last = _last_seen(calls, _is_hosted(key), key)
        rows.append(
            EngineRow(
                key=key,
                label=label,
                model=one.model if one is not None else "",
                where="",
                outside=True,
                state=state,
                last_answered=last[0],
                last_seconds=last[1],
                last_silent_at=last[2],
                last_silent_why=last[3],
            )
        )

    total = Tally()
    fallback = 0

    for call in calls:
        total = total.counting(call)
        fallback += 1 if silent_of(call.route) else 0

    return EnginesView(
        engines=tuple(rows),
        callers=tuple(sorted(policy.callers.items())),
        kinds=tuple(sorted(policy.kinds.items())),
        table=tuple(policy.preferences.items()),
        total=total,
        by_caller=_tally(calls, lambda call: call.caller),
        by_kind=_tally(calls, lambda call: call.kind),
        by_engine=_tally(calls, answerer),
        with_fallback=fallback,
        recent=calls[:shown],
    )
