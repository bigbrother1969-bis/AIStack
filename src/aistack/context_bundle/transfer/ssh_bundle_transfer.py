from pathlib import Path
import subprocess

from aistack.contracts.bundle_transfer import (
    BundleTransfer,
)


class SshBundleTransfer(BundleTransfer):
    """
    SSH based Context Bundle transfer.

    Uses external transport commands.
    Transport details remain outside
    the knowledge model.
    """

    def transfer(
        self,
        source: Path,
        target: str,
    ) -> bool:

        source = Path(source)

        subprocess.run(
            [
                "scp",
                str(source),
                target,
            ],
            check=True,
        )

        return True
