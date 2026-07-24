from pathlib import Path

from aistack.context_bundle.transfer.service import (
    DefaultContextBundleTransferService,
)

from aistack.context_bundle.transfer.policy import (
    DefaultBundleTransferPolicy,
)

from aistack.context_bundle.transfer.bundle_transfer import (
    FileSystemBundleTransfer,
)


def test_transfer_service_disabled(tmp_path):

    service = DefaultContextBundleTransferService(
        DefaultBundleTransferPolicy(),
        FileSystemBundleTransfer(),
    )

    result = service.transfer(
        tmp_path / "bundle.zip"
    )

    assert result is False



def test_transfer_service_enabled(tmp_path):

    source = tmp_path / "bundle.zip"

    source.write_text(
        "bundle",
        encoding="utf-8",
    )

    target = tmp_path / "laptop"


    service = DefaultContextBundleTransferService(
        DefaultBundleTransferPolicy(
            _enabled=True,
            _target=str(target),
        ),
        FileSystemBundleTransfer(),
    )


    result = service.transfer(
        source
    )


    assert result is True

    assert (
        target / "bundle.zip"
    ).exists()
