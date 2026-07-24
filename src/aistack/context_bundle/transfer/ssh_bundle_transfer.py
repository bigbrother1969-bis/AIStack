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
                str(source),
                target,
            ],
            check=True,
        )

        return True
