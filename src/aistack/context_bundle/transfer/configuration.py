from dataclasses import dataclass

from aistack.contracts.bundle_transfer_configuration import (
    BundleTransferConfiguration,
)


@dataclass(frozen=True)
class DefaultBundleTransferConfiguration(
    BundleTransferConfiguration
):
    """
    Default configuration for Context Bundle transfer.
    """

    _enabled: bool
    _host: str
    _user: str
    _destination_path: str


    @property
    def enabled(self) -> bool:
        return self._enabled


    @property
    def host(self) -> str:
        return self._host


    @property
    def user(self) -> str:
        return self._user


    @property
    def destination_path(self) -> str:
        return self._destination_path
