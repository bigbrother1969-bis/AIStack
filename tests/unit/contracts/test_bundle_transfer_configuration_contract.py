from aistack.contracts.bundle_transfer_configuration import (
    BundleTransferConfiguration,
)


class DummyTransferConfiguration(
    BundleTransferConfiguration
):

    @property
    def enabled(self):
        return True


    @property
    def host(self):
        return "laptop"


    @property
    def user(self):
        return "big-brother"


    @property
    def destination_path(self):
        return "~/Téléchargements"


def test_bundle_transfer_configuration_contract():

    config = DummyTransferConfiguration()

    assert config.enabled is True

    assert config.host == "laptop"

    assert config.user == "big-brother"

    assert config.destination_path == "~/Téléchargements"
