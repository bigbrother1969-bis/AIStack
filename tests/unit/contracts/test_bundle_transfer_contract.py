from pathlib import Path

from aistack.contracts.bundle_transfer import (
    BundleTransfer,
)


class DummyBundleTransfer(BundleTransfer):

    def transfer(
        self,
        source: Path,
        target: str,
    ) -> bool:

        return True


def test_bundle_transfer_contract():

    transfer = DummyBundleTransfer()

    result = transfer.transfer(
        Path("bundle.zip"),
        "laptop",
    )

    assert result is True
