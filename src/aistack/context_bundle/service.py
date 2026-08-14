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

        # Outcome of the last delivery attempt.
        # None means "no failure observed".
        self.transfer_error: Exception | None = None


    def generate(
        self,
        source_path: Path,
        output_path: Path,
        source_commit: str,
        repository_url: str = "unknown",
    ):

        bundle = self.engine.build(
            source_path,
            output_path,
            source_commit,
            repository_url,
        )

        self.transfer_error = None

        if self.transfer_service:

            # Generation and delivery are distinct
            # responsibilities. A delivery failure must not
            # destroy a valid bundle, and must not be
            # silently ignored either: it is recorded and
            # remains visible to the caller.
            try:
                self.transfer_service.transfer(
                    output_path
                )

            except Exception as error:
                self.transfer_error = error

        return bundle
