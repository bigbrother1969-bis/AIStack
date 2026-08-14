from pathlib import Path
import subprocess

from aistack.contracts.bundle_transfer import (
    BundleTransfer,
)

from aistack.contracts.bundle_transfer_configuration import (
    BundleTransferConfiguration,
)

from aistack.context_bundle.transfer.configuration import (
    DefaultBundleTransferConfiguration,
)


class SshBundleTransfer(BundleTransfer):
    """
    SSH based Context Bundle transfer.

    Uses external transport commands.

    Transport destination is governed by
    BundleTransferConfiguration.

    The transfer is non-interactive by design: an
    unattended pipeline must fail explicitly rather than
    block on a credential prompt.
    """

    def __init__(
        self,
        config: BundleTransferConfiguration | None = None,
    ):
        self.configuration = (
            config
            or DefaultBundleTransferConfiguration(
                _enabled=False,
                _host="",
                _user="",
                _destination_path="",
            )
        )


    def transfer(
        self,
        source: Path,
    ) -> bool:

        source = Path(source)

        target = (
            f"{self.configuration.user}"
            f"@"
            f"{self.configuration.host}"
            f":"
            f"{self.configuration.destination_path}"
        )

        subprocess.run(
            [
                "scp",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=accept-new",
                str(source),
                target,
            ],
            check=True,
        )

        return True
