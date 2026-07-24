from pathlib import Path

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.context_bundle_service import (
    ContextBundleService,
)

from aistack.context_bundle.engine import (
    DefaultContextBundleEngine,
)


class DefaultContextBundleService(ContextBundleService):
    """
    Application service exposing Context Bundle generation.
    """

    def __init__(self):

        self.engine = DefaultContextBundleEngine()


    def generate(
        self,
        source_path: Path,
        output_path: Path,
        source_commit: str,
    ) -> ContextBundle:

        return self.engine.build(
            source_path,
            output_path,
            source_commit,
        )
