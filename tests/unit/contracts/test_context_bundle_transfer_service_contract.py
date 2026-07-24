from pathlib import Path

from aistack.contracts.context_bundle_transfer_service import (
    ContextBundleTransferService,
)


class DummyContextBundleTransferService(
    ContextBundleTransferService
):

    def transfer(
        self,
        bundle_path: Path,
    ) -> bool:

        return True


def test_context_bundle_transfer_service_contract():

    service = DummyContextBundleTransferService()

    assert service.transfer(
        Path("bundle.zip")
    ) is True
