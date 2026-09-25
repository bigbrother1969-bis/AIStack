from __future__ import annotations

import subprocess
from pathlib import Path

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.providers.docker import DockerProvider
from aistack.providers.host.provider import HostProvider
from aistack.runtime.evaluate import evaluate
from aistack.runtime.idle_consumption import find_unexplained_consumption

# **Duplicated from `aistack.cli.runtime_diagnose`, not imported —
# the same choice, for the same reason, `aistack.cli.console_render`
# already documents for its own four domain functions against
# `aistack.cli.health_render`: "no CLI in this package imports
# another." `runtime_diagnose.py` produces eleven different kinds of
# finding across five domains and never persists any of them; this
# command needs only the one narrow slice the owner chose as J6's
# real subject (2026-09-13) — the `evaluate()` correlation J5 already
# built and closed (`claude/PLAN-J5-EVALUATE-QUALIFIED-FINDING-2026
# -09-11.md`) — so it collects exactly what that correlation needs
# and nothing else `runtime_diagnose.py` also collects. A drift-guard
# test compares this path against `runtime_diagnose`'s own.
DEFAULT_RESOURCE_PRIORITY = (
    Path(__file__).resolve().parents[1]
    / "priority"
    / "definitions"
    / "resource_priority.yml"
)

# Same convention as every other CLI's own `DEFAULT_*` constant in
# this package — a `Path(__file__).resolve()`-relative default.
DEFAULT_AI_RUNTIME = (
    Path(__file__).resolve().parents[1]
    / "ai_runtime"
    / "definitions"
    / "ai_runtime.yml"
)


def resource_priority_definition(
    path: Path,
) -> tuple[ResourcePriorityDefinition | None, str]:
    """Mirrors `aistack.cli.runtime_diagnose.resource_priority_definition` exactly."""

    if not path.exists():
        return None, (
            f"no resource-priority definition at {path}; consumption "
            f"is not checked"
        )

    try:
        return load_resource_priority_yaml(path), ""
    except (ValueError, OSError) as error:
        return None, (
            f"resource-priority definition not readable ({error}); "
            f"consumption is not checked"
        )


def qualified_findings() -> tuple[tuple[RuntimeFinding, ...], str]:
    """
    Every `RuntimeFinding` `aistack.runtime.evaluate.evaluate` can
    produce right now, freshly collected — J6's declared real subject
    (2026-09-13), the same correlation J5 already closed.

    Returns the findings and a note explaining why there may be none —
    no resource-priority definition declared, or CPU readings that
    could not be collected — never raises.
    """

    definition, note = resource_priority_definition(DEFAULT_RESOURCE_PRIORITY)

    if definition is None:
        return (), note

    try:
        readings = DockerProvider().collect_cpu_readings()
    except (subprocess.SubprocessError, OSError) as error:
        return (), (
            f"CPU readings could not be collected ({error}); "
            f"nothing to reason about"
        )

    consumption = find_unexplained_consumption(readings, definition)

    # `HostProvider.collect_temperatures` is documented never to
    # raise, the same convention `runtime_diagnose.py` already relies
    # on for the same call.
    temperatures = HostProvider().collect_temperatures()

    return evaluate(consumption, temperatures), ""


def report(finding: RuntimeFinding, answers: tuple[AIRuntimeAnswer, ...]) -> None:
    print(f"[{finding.subject}] {finding.signature}")
    print(f"    {finding.interpretation}")
    print("")

    for answer in answers:
        print(f"  {answer.operation}:")

        if not answer.reachable:
            print(f"    (not answered — {answer.unreachable_reason})")
            print("")
            continue

        for line in answer.response.strip().splitlines():
            print(f"    {line}")

        print("")


def main() -> None:
    ai_runtime_definition = load_ai_runtime_yaml(DEFAULT_AI_RUNTIME)

    findings, note = qualified_findings()

    if note:
        print(f"AI Runtime: {note}")

    if not findings:
        print("No qualified finding to reason about right now.")
        return

    # Built even when `model` is empty — `aistack.ai_runtime
    # .operations._ask` returns before ever calling `engine.complete`
    # in that case (`AIRuntimeDefinition.model`'s own docstring), so
    # this engine is constructed but never actually asked anything.
    #
    # `timeout` is passed through from the declaration rather than
    # left at `OllamaEngine`'s own default — a slower, more reliable
    # model (`deepseek-r1:1.5b`, `AIRuntimeDefinition.timeout`'s own
    # docstring) needs its declared, longer timeout honored here, not
    # silently reset to 120s on every real call.
    engine = OllamaEngine(
        host=ai_runtime_definition.host,
        port=ai_runtime_definition.port,
        model=ai_runtime_definition.model or "",
        timeout=ai_runtime_definition.timeout,
    )

    for finding in findings:
        answers = (
            reason(finding, engine, ai_runtime_definition.model),
            explain(finding, engine, ai_runtime_definition.model),
            recommend(finding, engine, ai_runtime_definition.model),
        )

        # J7, AI Reasoning History — traced unconditionally, even
        # when every answer above is `reachable=False`: an engine
        # that could not be reached is itself a real outcome worth
        # keeping (`aistack.ai_runtime.reasoning_history`'s own
        # docstring), not a case to skip persisting.
        record_ai_reasoning(finding, answers)

        report(finding, answers)


if __name__ == "__main__":
    main()
