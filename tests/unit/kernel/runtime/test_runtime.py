from aistack.kernel.runtime import KernelRuntime, RuntimeState


def test_runtime_boot() -> None:
    runtime = KernelRuntime.boot()

    assert runtime.state == RuntimeState.READY
    assert runtime.kernel is not None


def test_runtime_transport() -> None:
    runtime = KernelRuntime.boot()

    assert runtime.transport is runtime.kernel.services.transport
