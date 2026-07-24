from pathlib import Path

from aistack.context_bundle.transfer.bundle_transfer import (
    FileSystemBundleTransfer,
)


def test_filesystem_bundle_transfer(tmp_path):

    source = (
        tmp_path
        / "source"
        / "bundle.zip"
    )

    source.parent.mkdir()

    source.write_text(
        "bundle",
        encoding="utf-8",
    )


    target = (
        tmp_path
        / "target"
    )


    transfer = FileSystemBundleTransfer()


    result = transfer.transfer(
        source,
        str(target),
    )


    assert result is True

    assert (
        target / "bundle.zip"
    ).exists()
