from pathlib import Path

from aistack.context_bundle.service import (
    DefaultContextBundleService,
)


class FakeEngine:

    def __init__(self):
        self.calls = []

    def build(
        self,
        source_path,
        output_path,
        source_commit,
        repository_url="unknown",
    ):
        self.calls.append(source_commit)
        return "bundle"


class FailingTransfer:

    def transfer(self, source):
        raise RuntimeError("scp exit status 255")


class WorkingTransfer:

    def __init__(self):
        self.transferred = []

    def transfer(self, source):
        self.transferred.append(source)
        return True


def _generate(service):
    return service.generate(
        source_path=Path("/tmp/src"),
        output_path=Path("/tmp/out.zip"),
        source_commit="abcdef",
    )


def test_delivery_failure_does_not_destroy_the_bundle():
    """
    Generation and delivery are distinct responsibilities.
    A transport failure must not invalidate a bundle that
    was correctly produced.
    """

    service = DefaultContextBundleService(
        engine=FakeEngine(),
        transfer_service=FailingTransfer(),
    )

    bundle = _generate(service)

    assert bundle == "bundle"


def test_delivery_failure_remains_visible():
    """
    Nothing is silently ignored: the failure is recorded
    and observable by the caller.
    """

    service = DefaultContextBundleService(
        engine=FakeEngine(),
        transfer_service=FailingTransfer(),
    )

    _generate(service)

    assert service.transfer_error is not None

    assert "255" in str(service.transfer_error)


def test_successful_delivery_records_no_error():

    transfer = WorkingTransfer()

    service = DefaultContextBundleService(
        engine=FakeEngine(),
        transfer_service=transfer,
    )

    _generate(service)

    assert service.transfer_error is None

    assert transfer.transferred == [Path("/tmp/out.zip")]


def test_no_transfer_service_is_not_a_failure():

    service = DefaultContextBundleService(
        engine=FakeEngine(),
        transfer_service=None,
    )

    _generate(service)

    assert service.transfer_error is None
