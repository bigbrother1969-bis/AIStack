from __future__ import annotations

from aistack.config import configured

import subprocess
from functools import partial
from pathlib import Path

from aistack.ai_runtime.call_journal import VIGIL_REASON, journaled
from aistack.ai_runtime.reasoning_history import record_ai_reasoning
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.kernel.bootstrap import registered_providers
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.kernel.registries import ProviderRegistry
from aistack.providers.docker import DockerProvider
from aistack.providers.host.provider import HostProvider
from aistack.runtime.evaluate import evaluate
from aistack.runtime.idle_consumption import find_unexplained_consumption
from aistack.troubleshooting.guide import ask_managed

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


def qualified_findings(
    providers: ProviderRegistry | None = None,
) -> tuple[tuple[RuntimeFinding, ...], str]:
    """
    Collect what `aistack.runtime.evaluate.evaluate` needs and return its findings.

    Returns the findings and a note explaining why there may be none (no
    resource-priority definition, or CPU readings not collected); never raises.
    """

    definition, note = resource_priority_definition(DEFAULT_RESOURCE_PRIORITY)

    if definition is None:
        return (), note

    # One Kernel for both readings (ADR-0027 § 9): the Task's own registry.
    providers = registered_providers(providers)

    try:
        readings = providers.get_as("docker", DockerProvider).collect_cpu_readings()
    except (subprocess.SubprocessError, OSError) as error:
        return (), (
            f"CPU readings could not be collected ({error}); "
            f"nothing to reason about"
        )

    consumption = find_unexplained_consumption(readings, definition)

    # Never raises.
    temperatures = providers.get_as("host", HostProvider).collect_temperatures()

    return evaluate(consumption, temperatures), ""


class AiReasonTask:
    """
    Reason about what the host's findings say, with the AI runtime
    (`ai.reason`, ADR-0027 § 10).

    The sixth chain the Runtime executes. It collects the qualified
    findings through the providers the Kernel registered, asks the model
    to reason about, explain and recommend on each, and records each
    round in the AI Reasoning History (read by the Time Machine), even
    when no answer was reachable: that is an outcome too.

    The engines are the declared ones (`ask_local`: Ollama alone, or the
    ordered `engines:` with hand-over and, for an engine that declares one,
    the switch that starts it on demand), built at use. Nothing secret
    passes through the request, which carries no payload.

    Returns an Observation of plain values: the note that explains why
    there may be no finding, and for each finding what was asked and
    answered, for the command to print.
    """

    task_id = "ai.reason"
    task_name = "AI reasoning"

    def __init__(self, providers: ProviderRegistry) -> None:
        self._providers = providers

    def execute(self, request: Request) -> Observation:
        ai_runtime_definition = load_ai_runtime_yaml(DEFAULT_AI_RUNTIME)

        findings, note = qualified_findings(self._providers)

        reasoned: list[dict[str, object]] = []

        if findings:
            for finding in findings:
                # The same engines, in the same order, with the same hand-over and the same switch as
                # the console's pages: the watch is one more reader of `engines:`, not a path of its own.
                ask = journaled(partial(ask_managed, VIGIL_REASON), VIGIL_REASON)
                answers = tuple(
                    ask(finding, operation, "fr", definition=ai_runtime_definition)
                    for operation in ("reason", "explain", "recommend")
                )

                record_ai_reasoning(finding, answers)

                reasoned.append(
                    {
                        "subject": finding.subject,
                        "signature": finding.signature,
                        "interpretation": finding.interpretation,
                        "answers": [
                            {
                                "operation": answer.operation,
                                "reachable": answer.reachable,
                                "response": answer.response,
                                "unreachable_reason": answer.unreachable_reason,
                            }
                            for answer in answers
                        ],
                    }
                )

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={"note": note, "findings": reasoned},
        )
