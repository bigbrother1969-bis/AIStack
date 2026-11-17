"""
The trace of a Task is a historised stream like the others: the data
budget measures it and compresses it after 90 days (ADR-0021 § 3,
ADR-0027 § 10, commit 5.3). Nothing else makes that so, so these tests
do: a trace kept somewhere else would silently leave the compaction.
"""

from __future__ import annotations

import gzip
from datetime import datetime, timezone
from pathlib import Path

from aistack.data_budget.budget import compress_old, load_data_budget, measure
from aistack.history import every_version
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.kernel.resolution import ResolutionResult
from aistack.kernel.tracing import ExecutionTrace, FileTraceRepository
from aistack.kernel.tracing.repository.file import DEFAULT_OUTPUT_PATH


class _Task:
    task_id = "task.fake"
    task_name = "Fake Task"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def _trace() -> ExecutionTrace:
    request = Request(request_id="request-001", task_id="task.fake")
    return ExecutionTrace(
        request=request,
        resolution=ResolutionResult(task=_Task(), resolver="TaskResolver", reason="resolved"),
        observation=Observation(
            context=ObservationContext(
                request_id="request-001",
                component_type="task",
                component_id="task.fake",
                operation="execute",
            )
        ),
    )


def test_the_default_trace_path_is_the_one_the_owner_decided() -> None:
    assert DEFAULT_OUTPUT_PATH == Path("reports/generated/execution-trace.json")


def test_an_old_trace_is_compressed_and_still_read(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    FileTraceRepository(output_path=generated / "execution-trace.json").save(_trace())

    history = generated / "history" / "execution-trace"
    (written,) = history.glob("*.json")
    old = history / "2026-06-01T10-00-00Z.json"
    content = written.read_text(encoding="utf-8")
    written.rename(old)

    budget = load_data_budget()
    assert measure(generated, budget).files >= 2

    done = compress_old(generated, budget, now=datetime(2026, 11, 17, tzinfo=timezone.utc))

    assert done.problems == []
    assert done.files == 1
    assert not old.exists()
    assert gzip.decompress(old.with_name(old.name + ".gz").read_bytes()).decode("utf-8") == content
    assert len(every_version(generated, "execution-trace")) == 1
