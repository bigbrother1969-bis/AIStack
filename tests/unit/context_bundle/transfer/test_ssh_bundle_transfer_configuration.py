from pathlib import Path

from aistack.context_bundle.transfer.configuration import (
    DefaultBundleTransferConfiguration,
)

from aistack.context_bundle.transfer.ssh_bundle_transfer import (
    SshBundleTransfer,
)


def test_ssh_transfer_uses_configuration():

    config = DefaultBundleTransferConfiguration(
        _enabled=True,
        _host="laptop",
        _user="big-brother",
        _destination_path="~/Téléchargements",
    )

    transfer = SshBundleTransfer(
        config=config,
    )

    assert transfer.configuration.host == "laptop"

    assert transfer.configuration.user == "big-brother"

    assert (
        transfer.configuration.destination_path
        == "~/Téléchargements"
    )
