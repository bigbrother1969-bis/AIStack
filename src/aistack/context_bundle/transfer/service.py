from pathlib import Path

from aistack.contracts.bundle_transfer import (
    BundleTransfer,
)

from aistack.contracts.bundle_transfer_policy import (
    BundleTransferPolicy,
)

from aistack.contracts.context_bundle_transfer_service import (
    ContextBundleTransferService,
)


class DefaultContextBundleTransferService(
    ContextBundleTransferService
):
    """
    Default Context Bundle transfer orchestration service.
    """

    def __init__(
        self,
        policy: BundleTransferPolicy,
        transfer: BundleTransfer,
    ):
        self.policy = policy
        self.transfer_engine = transfer


    def transfer(
        self,
        bundle_path: Path,
    ) -> bool:

        if not self.policy.enabled:
            return False

        return self.transfer_engine.transfer(
            bundle_path,
            self.policy.target,
        )
