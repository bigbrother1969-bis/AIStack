from pathlib import Path

from aistack.context_bundle.transfer.ssh_bundle_transfer import (
    SshBundleTransfer,
)


def test_ssh_bundle_transfer_contract():

    transfer = SshBundleTransfer()

    assert isinstance(
        transfer,
        object,
    )
