from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.time import Provenance, next_version_from_history
from aistack.kernel.tracing.repository.contract import TraceRepository
from aistack.kernel.tracing.serialization import serialize_execution_trace
from aistack.kernel.tracing.trace import ExecutionTrace


DEFAULT_OUTPUT_PATH = Path("reports/generated/execution-trace.json")


@dataclass
class FileTraceRepository(TraceRepository):
    """
    Durable trace repository.

    `get_all()` returns the traces saved by this process, kept in
    memory. `save()` also writes each trace to disk with
    `write_artifact_with_history`, so it outlives the process; the
    version is counted from history on disk and the provenance names
    the task and the request.

    Traces are not read back: `resolution.task` is a live object, so
    history holds only the serialized `dict`.
    """

    output_path: Path = field(default_factory=lambda: DEFAULT_OUTPUT_PATH)
    traces: list[ExecutionTrace] = field(default_factory=list)

    def save(
        self,
        trace: ExecutionTrace,
    ) -> None:
        self.traces.append(trace)

        version = next_version_from_history(
            self.output_path.parent, self.output_path.stem
        )
        provenance = Provenance(
            origin=trace.resolution.task.task_id,
            causality=trace.request.request_id,
        )

        content = (
            json.dumps(
                serialize_execution_trace(
                    trace, version=version, provenance=provenance
                ),
                indent=2,
                ensure_ascii=False,
                default=str,
            )
            + "\n"
        )

        write_artifact_with_history(content, self.output_path)

    def get_all(
        self,
    ) -> tuple[ExecutionTrace, ...]:
        return tuple(self.traces)
