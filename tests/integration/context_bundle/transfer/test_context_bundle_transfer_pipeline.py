from pathlib import Path

from aistack.context_bundle.service import (
    DefaultContextBundleService,
)

from aistack.context_bundle.transfer.policy import (
    DefaultBundleTransferPolicy,
)

from aistack.context_bundle.transfer.service import (
    DefaultContextBundleTransferService,
)

from aistack.context_bundle.transfer.bundle_transfer import (
    FileSystemBundleTransfer,
)



def test_context_bundle_transfer_pipeline(tmp_path):

    source = tmp_path / "knowledge"
    source.mkdir()

    (source / "principle.md").write_text(
        "# Principle\n",
        encoding="utf-8",
    )


    bundle_output = (
        tmp_path
        / "bundle.zip"
    )


    transfer_target = (
        tmp_path
        / "laptop"
    )


    transfer_service = (
        DefaultContextBundleTransferService(
            DefaultBundleTransferPolicy(
                _enabled=True,
                _target=str(transfer_target),
                _strategy="filesystem",
            ),
            FileSystemBundleTransfer(),
        )
    )


    service = DefaultContextBundleService(
        transfer_service=transfer_service,
    )


    bundle = service.generate(
        source,
        bundle_output,
        "commit123",
    )


    assert bundle.source_commit == "commit123"

    assert bundle_output.exists()

    assert (
        transfer_target
        / "bundle.zip"
    ).exists()
