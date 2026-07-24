from aistack.contracts.transfer_target import (
    TransferTarget,
)


class DummyTransferTarget(
    TransferTarget
):

    @property
    def host(self):
        return "laptop"

    @property
    def user(self):
        return "big-brother"

    @property
    def path(self):
        return "/tmp/context"


def test_transfer_target_contract():

    target = DummyTransferTarget()

    assert target.host == "laptop"
    assert target.user == "big-brother"
    assert target.path == "/tmp/context"
