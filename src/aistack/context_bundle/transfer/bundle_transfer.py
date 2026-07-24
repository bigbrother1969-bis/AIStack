from pathlib import Path
import shutil

from aistack.contracts.bundle_transfer import (
    BundleTransfer,
)


class FileSystemBundleTransfer(BundleTransfer):
    """
    Local filesystem Context Bundle transfer.

    First implementation of bundle portability.
    """

    def transfer(
        self,
        source: Path,
        target: str,
    ) -> bool:

        source = Path(source)

        destination = Path(target)

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination / source.name,
        )

        return (
            destination / source.name
        ).exists()
