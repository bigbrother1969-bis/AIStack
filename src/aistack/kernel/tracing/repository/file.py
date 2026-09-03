from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.tracing.repository.contract import TraceRepository
from aistack.kernel.tracing.serialization import serialize_execution_trace
from aistack.kernel.tracing.trace import ExecutionTrace


DEFAULT_OUTPUT_PATH = Path("reports/generated/execution-trace.json")


@dataclass
class FileTraceRepository(TraceRepository):
    """
    Durable trace repository — Runtime Operation History,
    2026-09-03, the historisation workstream's third dimension after
    Observation History (providers) and its own prerequisite,
    GOV-0002/OS-045 (a first Task registered and executed in
    production, without which a trace would have nothing real to
    persist).

    **Two responsibilities, kept separate on purpose.**
    `get_all()` answers "what has this process executed", the same
    question `InMemoryTraceRepository` already answers and the one
    `KernelRuntime`'s own tests depend on
    (`tests/unit/kernel/runtime/test_runtime_execution.py`) — so this
    class keeps an in-memory list exactly like that one, rather than
    reading every trace back off disk on every call. `save()`
    additionally writes each trace to disk, through
    `write_artifact_with_history` — the same mechanism, same
    retention decision ("keep everything, indefinitely",
    2026-09-03), already governing every provider observation — so a
    trace outlives the process that produced it and is queryable the
    same way (`aistack.cli.history_query execution-trace <instant>`).

    **Not the default `KernelRuntime.boot()` uses.** Every existing
    caller of `.boot()` — the Runtime's own test suite among them —
    gets `InMemoryTraceRepository` unless it asks for this one
    explicitly (`KernelRuntime.boot(trace_repository=
    FileTraceRepository())`), the same way `aistack.cli.
    docker_discover` does. Defaulting `.boot()` itself to this class
    would have every test that calls it write real files into the
    repository's own `reports/generated/` — most of them do not
    `chdir` to an isolated directory, unlike the CLI tests that do —
    which is not a decision to make silently inside a constructor.

    **Reconstructing an `ExecutionTrace` from disk is not offered,
    and cannot be, faithfully.** `serialize_execution_trace` already
    documents why: `resolution.task` is a live executable, not data,
    so nothing read back from JSON can rebuild the same
    `ResolutionResult`. What a reader gets back from history is the
    serialized `dict` (`aistack.kernel.tracing.serialization
    .serialize_execution_trace`'s own shape) — accurate to what
    happened, not a promise that it round-trips to the original
    object.
    """

    output_path: Path = field(default_factory=lambda: DEFAULT_OUTPUT_PATH)
    traces: list[ExecutionTrace] = field(default_factory=list)

    def save(
        self,
        trace: ExecutionTrace,
    ) -> None:
        self.traces.append(trace)

        content = (
            json.dumps(
                serialize_execution_trace(trace),
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
