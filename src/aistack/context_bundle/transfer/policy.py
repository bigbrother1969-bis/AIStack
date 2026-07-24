from dataclasses import dataclass

from aistack.contracts.bundle_transfer_policy import (
    BundleTransferPolicy,
)


@dataclass(frozen=True)
class DefaultBundleTransferPolicy(
    BundleTransferPolicy
):
    """
    Default Context Bundle transfer policy.
    """

    _enabled: bool = False
    _target: str = ""
    _strategy: str = "filesystem"


    @property
    def enabled(self) -> bool:
        return self._enabled


    @property
    def target(self) -> str:
        return self._target


    @property
    def strategy(self) -> str:
        return self._strategy
