from pathlib import Path

from aistack.context_bundle.engine import (
    DefaultContextBundleEngine,
)

from aistack.contracts.context_bundle_transfer_service import (
    ContextBundleTransferService,
)


class DefaultContextBundleService:
    """
    Main Context Bundle orchestration service.
    """

    def __init__(
        self,
        engine=None,
        transfer_service: ContextBundleTransferService | None = None,
    ):
        self.engine = (
            engine
            or DefaultContextBundleEngine()
        )

        self.transfer_service = transfer_service


    def generate(
        self,
        source_path: Path,
        output_path: Path,
        source_commit: str,
    ):

        bundle = self.engine.build(
            source_path,
            output_path,
            source_commit,
        )

        if self.transfer_service:
            self.transfer_service.transfer(
                output_path
            )

        return bundle
