from aistack.kernel.runtime import KernelRuntime, RuntimeState
from aistack.kernel.tracing import FileTraceRepository, InMemoryTraceRepository


def test_runtime_boot() -> None:
    runtime = KernelRuntime.boot()

    assert runtime.state == RuntimeState.READY
    assert runtime.kernel is not None


def test_runtime_transport() -> None:
    runtime = KernelRuntime.boot()

    assert runtime.transport is runtime.kernel.services.transport


def test_boot_defaults_to_an_in_memory_trace_repository() -> None:
    """
    2026-09-03: `boot()` gained a `trace_repository` parameter for
    `FileTraceRepository`. Every caller that does not ask for it —
    the Runtime's own test suite included, most of which never
    `chdir`s to an isolated directory — must keep getting the
    in-memory one, or those tests would start writing real files
    into this repository's `reports/generated/`.
    """

    runtime = KernelRuntime.boot()

    assert isinstance(runtime.trace_repository, InMemoryTraceRepository)


def test_boot_accepts_an_explicit_trace_repository(tmp_path) -> None:
    repository = FileTraceRepository(output_path=tmp_path / "execution-trace.json")

    runtime = KernelRuntime.boot(trace_repository=repository)

    assert runtime.trace_repository is repository
