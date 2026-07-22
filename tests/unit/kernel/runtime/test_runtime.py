from aistack.kernel.runtime import KernelRuntime, RuntimeState


def test_runtime_boot():
    runtime = KernelRuntime.boot()

    assert runtime.state == RuntimeState.READY
    assert runtime.kernel is not None


def test_runtime_transport():
    runtime = KernelRuntime.boot()

    assert runtime.transport is runtime.kernel.services.transport
