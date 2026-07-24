from aistack.context_bundle.transfer.configuration import (
    DefaultBundleTransferConfiguration,
)


def test_default_transfer_configuration():

    config = DefaultBundleTransferConfiguration(
        _enabled=True,
        _host="laptop",
        _user="big-brother",
        _destination_path="~/Téléchargements",
    )

    assert config.enabled is True

    assert config.host == "laptop"

    assert config.user == "big-brother"

    assert config.destination_path == "~/Téléchargements"
