"""
GOV-0002/OS-041 measured, 2026-08-27: `KernelRuntime.boot()` called
by tests only, tasks registered → 0 — "the dimension is not merely
uncalled, it has nothing to execute." Resolved that day by declaring
the Execution Dimension unearned, on the condition that it "awaits a
real need" and names its own reopening test: "turning one [provider
CLI] into a registered task is the measurement that would tell
whether the abstraction earns itself."

This file is that measurement, taken 2026-09-03. `docker_discover`
now goes through `KernelRuntime.execute()`, not a direct provider
call — this proves the whole chain a human running the command
depends on, not just `DockerDiscoverTask` in isolation
(`tests/unit/kernel/tasks/test_docker_discover_task.py`) or its
registration (`tests/unit/kernel/bootstrap/test_tasks.py`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import docker_discover
from aistack.kernel.tracing import ExecutionTraceEventType


OBSERVED_AT = "2026-09-03T09:00:00+00:00"


class FakeDockerProvider:
    def collect(self) -> dict[str, Any]:
        return {
            "provider": {"id": "aistack.provider.docker"},
            "collected_at": OBSERVED_AT,
            "docker": {"containers": []},
        }


@pytest.fixture
def stubbed_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "aistack.kernel.bootstrap.providers.DockerProvider",
        FakeDockerProvider,
    )


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_it_produces_a_real_execution_trace_end_to_end(stubbed_provider, workspace):
    """
    The condition GOV-0002/OS-041 measured false, measured true: a
    real `Request`, resolved against a real registered `Task`,
    executed, observed, traced — all five phases, not a stub
    standing in for the Runtime.
    """

    from aistack.kernel.runtime import KernelRuntime, Request

    runtime = KernelRuntime.boot()

    request = Request(request_id="test-request", task_id="docker.discover")
    trace = runtime.execute(request)

    assert [event.event_type for event in trace.events] == [
        ExecutionTraceEventType.REQUEST_RECEIVED,
        ExecutionTraceEventType.RESOLUTION_STARTED,
        ExecutionTraceEventType.RESOLUTION_COMPLETED,
        ExecutionTraceEventType.TASK_EXECUTED,
        ExecutionTraceEventType.OBSERVATION_PRODUCED,
    ]
    assert trace.resolution.task.task_id == "docker.discover"
    assert runtime.trace_repository.get_all() == (trace,)


def test_the_cli_itself_writes_the_observation_through_the_runtime(
    stubbed_provider, workspace, capsys
):
    docker_discover.main()

    output_path = workspace / "reports" / "generated" / "docker-provider-observation.json"
    observation = json.loads(output_path.read_text(encoding="utf-8"))

    assert observation["collected_at"] == OBSERVED_AT
    assert "reports/generated/docker-provider-observation.json" in (
        capsys.readouterr().out
    )


def test_two_cli_runs_get_different_request_ids(stubbed_provider, workspace, monkeypatch):
    """
    Each invocation is meant to be told apart once traces are
    historicised (the reason this command was migrated at all) —
    a fixed `request_id` would defeat that before it is even built.
    """

    seen: list[str] = []

    from aistack.kernel.runtime import KernelRuntime

    real_execute = KernelRuntime.execute

    def spy_execute(self, request):
        seen.append(request.request_id)
        return real_execute(self, request)

    monkeypatch.setattr(KernelRuntime, "execute", spy_execute)

    docker_discover.main()
    docker_discover.main()

    assert len(seen) == 2
    assert seen[0] != seen[1]
