"""
Which engines a call asks, and in which order (`ADR-0029` § 10).

A pure function of the declarations: the policy (class of the caller, kind of the
request, table of preferences) and what is declared and set (the outside engines,
the local ones). It reads no text of any question and asks nothing. It returns the
steps to try, best first, and what it left out and why, so the journal can say
both without a word of the content.

The class of the caller is a ceiling: an outside engine is never a step of an
`internal_only` caller, whatever the table says. A kind with no list, or a list
that leaves no engine, falls back to the order declared (outside engines, then the
local ones), within the same ceiling.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.ai_runtime.definition import LocalEngineDefinition
from aistack.ai_runtime.policy import EXTERNAL, AIPolicy

HOSTED = ("gemini", "openai", "anthropic")
LOCAL = "local"
DECLARED_ORDER = "declared order"


@dataclass(frozen=True)
class Step:
    """One engine to ask: an outside engine by name, or local engines (one, or all that are allowed, in order)."""

    engine: str
    why: str
    local: tuple[LocalEngineDefinition, ...] = ()

    @property
    def outside(self) -> bool:
        return self.engine in HOSTED


def _label(engine: LocalEngineDefinition) -> str:
    return engine.label or engine.model


def plan(
    policy: AIPolicy,
    caller: str,
    kind: str,
    declared: tuple[str, ...],
    set_now: tuple[str, ...],
    local_engines: tuple[LocalEngineDefinition, ...],
) -> tuple[tuple[Step, ...], tuple[str, ...]]:
    """
    The steps for a call of `caller` of this `kind`, and the engines passed over with the reason.

    `declared` are the outside engines declared in `ai_runtime.yml`, `set_now` those whose key is in
    the environment, `local_engines` the local ones as declared.
    """

    may_go_outside = policy.allows_external(caller)
    allowed_local = tuple(e for e in local_engines if may_go_outside or policy.kind_of_host(e.host) != EXTERNAL)
    passed_over: list[str] = []

    # An outside engine whose key is set but that this caller may not reach: said once, as the journal always has.
    if not may_go_outside:
        passed_over.extend(f"{name} (not allowed for this caller)" for name in set_now)
        passed_over.extend(
            f"{_label(e)} (outside your machines, not allowed for this caller)" for e in local_engines if e not in allowed_local
        )

    steps: list[Step] = []
    taken: set[str] = set()

    def add(step: Step) -> None:
        if step.engine not in taken:
            taken.add(step.engine)
            steps.append(step)

    for line in policy.preferred(kind):
        name = line.engine
        if name in HOSTED:
            if name not in declared:
                passed_over.append(f"{name} (not declared)")
            elif name not in set_now:
                passed_over.append(f"{name} (key not set)")
            elif may_go_outside:
                add(Step(name, line.why))
            # else: already said above, once, for every outside engine that is set.
        elif name == LOCAL:
            if allowed_local:
                add(Step(LOCAL, line.why, allowed_local))
            else:
                passed_over.append("local (none declared or allowed)")
        else:
            named = [e for e in local_engines if name.lower() in (e.label.lower(), e.model.lower())]
            if not named:
                passed_over.append(f"{name} (not declared)")
            elif named[0] not in allowed_local:
                pass  # already said above, once, for every local engine kept out
            else:
                add(Step(_label(named[0]), line.why, (named[0],)))

    if steps:
        return tuple(steps), tuple(passed_over)

    # No list for this kind, or nothing of it is left: the order declared, within the same ceiling.
    fallback: list[Step] = []
    if may_go_outside:
        fallback.extend(Step(name, DECLARED_ORDER) for name in HOSTED if name in set_now)
    if allowed_local or not local_engines:
        fallback.append(Step(LOCAL, DECLARED_ORDER, allowed_local))
    return tuple(fallback), tuple(passed_over)


def route_of(
    caller_class: str, kind: str, chose: Step | None, silent: tuple[tuple[str, str], ...], passed_over: tuple[str, ...]
) -> str:
    """
    What was decided, as one line of the journal: the class, the kind, the engine chosen and why, the
    engines asked that said nothing, the engines passed over and why. Declarations only, never content.
    """

    parts = [caller_class]
    if kind:
        parts.append(f"kind={kind}")
    if chose is not None:
        parts.append(f"chose {chose.engine}: {chose.why}")
    if silent:
        parts.append("silent: " + ", ".join(f"{name} ({reason[:60]})" for name, reason in silent))
    if passed_over:
        parts.append("passed over: " + ", ".join(passed_over))
    return "; ".join(parts)[:500]
