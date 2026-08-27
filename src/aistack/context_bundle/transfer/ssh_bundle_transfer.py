from pathlib import Path
import subprocess

from aistack.contracts.bundle_transfer_configuration import (
    BundleTransferConfiguration,
)

from aistack.context_bundle.transfer.configuration import (
    DefaultBundleTransferConfiguration,
)

from aistack.contracts.context_bundle_transfer_service import (
    ContextBundleTransferService,
)


class SshBundleTransfer(ContextBundleTransferService):
    """
    SSH based Context Bundle transfer.

    Uses external transport commands.

    Transport destination is governed by
    BundleTransferConfiguration.

    The transfer is non-interactive by design: an
    unattended pipeline must fail explicitly rather than
    block on a credential prompt.

    **It declared `BundleTransfer` until 2026-08-27 and did
    not implement it.** That contract is the transport —
    `transfer(source, target)`, the destination supplied by
    the caller — and this class takes one argument and builds
    its own destination from configuration. Python's ABC
    machinery checks that a method of the right *name* exists
    and never looks at its signature, so the class instantiated
    happily for weeks.

    `aistack.conformance.structural.satisfies` was not fooled —
    it compares call shapes, and never counted this class among
    `BundleTransfer`'s implementations. What nothing reports is
    the declaration itself: GOV-0002/OS-040.

    What it actually satisfies is `ContextBundleTransferService`
    — `transfer(bundle_path)` — which is the contract
    `DefaultContextBundleService` annotates its parameter with
    and the one every caller uses. The declaration is corrected
    to the contract that was always being honoured; no
    behaviour changes.

    **What the correction makes visible rather than fixes:**
    there are now two implementations of the orchestration
    contract — this one, which holds a configuration and no
    policy, and `DefaultContextBundleTransferService`, which
    holds a policy and delegates to a `BundleTransfer`. Only
    this one has a caller outside the tests. Which of them is
    the `BundleTransferManager` ADR-0007 names is unqualified,
    and the ADR's implementation table says so rather than
    guessing.
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
