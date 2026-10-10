from __future__ import annotations

from aistack.config import configured

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

DEFAULT_RESOURCE_PRIORITY = (
    configured(Path(__file__).resolve().parents[1]
    / "priority"
    / "definitions"
    / "resource_priority.yml")
)

DEFAULT_AI_RUNTIME = (
    configured(Path(__file__).resolve().parents[1]
    / "ai_runtime"
    / "definitions"
    / "ai_runtime.yml")
)


def resource_priority_definition(
    path: Path,
) -> tuple[ResourcePriorityDefinition | None, str]:
    """Load the resource-priority definition; (None, reason) when absent or unreadable."""

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
    Collect what `aistack.runtime.evaluate.evaluate` needs and return its findings.

    Returns the findings and a note explaining why there may be none (no
    resource-priority definition, or CPU readings not collected); never raises.
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

    # Never raises.
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

    # Built even when `model` is empty: the operations then return before
    # asking it. The declared timeout is passed on, since slower models
    # need more than `OllamaEngine`'s default.
    engine = OllamaEngine(
        host=ai_runtime_definition.host,
        port=ai_runtime_definition.port,
        model=ai_runtime_definition.model or "",
        timeout=ai_runtime_definition.timeout,
    )

    # A second, fast model translates answers into French when they are
    # not already; None when no `translator_model:` is declared.
    translator = (
        OllamaEngine(
            host=ai_runtime_definition.host,
            port=ai_runtime_definition.port,
            model=ai_runtime_definition.translator_model,
            timeout=ai_runtime_definition.timeout,
        )
        if ai_runtime_definition.translator_model
        else None
    )

    for finding in findings:
        answers = (
            reason(finding, engine, ai_runtime_definition.model, translator=translator),
            explain(finding, engine, ai_runtime_definition.model, translator=translator),
            recommend(finding, engine, ai_runtime_definition.model, translator=translator),
        )

        # Recorded even when no answer was reachable: that is an outcome too.
        record_ai_reasoning(finding, answers)

        report(finding, answers)


if __name__ == "__main__":
    main()
