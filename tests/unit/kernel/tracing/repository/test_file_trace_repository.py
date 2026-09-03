"""
`FileTraceRepository` — Runtime Operation History, 2026-09-03: the
durable trace repository, extending Observation History's own
`write_artifact_with_history` mechanism to executions instead of
provider observations.
"""

from __future__ import annotations

import json
from pathlib import Path

from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.kernel.resolution import ResolutionResult
from aistack.kernel.tracing import ExecutionPhase, ExecutionTrace, ExecutionTraceEvent
from aistack.kernel.tracing.event import ExecutionTraceEventType
from aistack.kernel.tracing.repository.file import FileTraceRepository


class FakeTask:
    task_id = "task.fake"
    task_name = "Fake Task"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def _trace(request_id: str = "request-001") -> ExecutionTrace:
    request = Request(request_id=request_id, task_id="task.fake")

    return ExecutionTrace(
        request=request,
        resolution=ResolutionResult(
            task=FakeTask(), resolver="TaskResolver", reason="resolved"
        ),
        observation=Observation(
            context=ObservationContext(
                request_id=request_id,
                component_type="task",
                component_id="task.fake",
                operation="execute",
            ),
            data={"n": 1},
        ),
        events=(
            ExecutionTraceEvent(
                phase=ExecutionPhase.REQUEST,
                event_type=ExecutionTraceEventType.REQUEST_RECEIVED,
                component="KernelRuntime",
                message="Runtime received request",
            ),
        ),
    )


def test_get_all_returns_every_trace_saved_this_process(tmp_path: Path):
    """Same contract as `InMemoryTraceRepository` — this is additive, not a replacement."""

    repository = FileTraceRepository(output_path=tmp_path / "execution-trace.json")

    first = _trace("request-001")
    second = _trace("request-002")

    repository.save(first)
    repository.save(second)

    assert repository.get_all() == (first, second)


def test_save_writes_the_latest_path(tmp_path: Path):
    output_path = tmp_path / "execution-trace.json"
    repository = FileTraceRepository(output_path=output_path)

    repository.save(_trace())

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["request"]["request_id"] == "request-001"


def test_save_keeps_observation_history_like_every_provider_artifact(tmp_path: Path):
    # Two real-clock writes can land in the same wall-clock second,
    # where a filename-string sort does not equal chronological
    # order (`aistack.history.query`'s own tests cover that) — this
    # only asserts both survive, as a set, not their filename order.
    output_path = tmp_path / "execution-trace.json"
    repository = FileTraceRepository(output_path=output_path)

    repository.save(_trace("request-001"))
    repository.save(_trace("request-002"))

    history_dir = output_path.parent / "history" / "execution-trace"
    history_files = list(history_dir.glob("*.json"))

    assert len(history_files) == 2
    contents = {
        json.loads(f.read_text(encoding="utf-8"))["request"]["request_id"]
        for f in history_files
    }
    assert contents == {"request-001", "request-002"}


def test_default_output_path_matches_reports_generated_convention():
    repository = FileTraceRepository()

    assert repository.output_path == Path("reports/generated/execution-trace.json")


def test_two_repository_instances_do_not_share_default_state(tmp_path: Path):
    """
    Mutation guard: a `field(default_factory=...)` was used rather
    than a bare mutable default specifically so two repositories (or
    the same one across two `KernelRuntime.boot()` calls) never
    share one traces list — the same class of bug Python's own
    "mutable default argument" trap produces.
    """

    first = FileTraceRepository(output_path=tmp_path / "a.json")
    second = FileTraceRepository(output_path=tmp_path / "b.json")

    first.save(_trace())

    assert second.get_all() == ()
