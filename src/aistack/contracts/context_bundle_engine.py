from abc import ABC, abstractmethod
from pathlib import Path

from aistack.contracts.context_bundle import ContextBundle


class ContextBundleEngine(ABC):
    """
    Contract for Context Bundle orchestration.
    """

    @abstractmethod
    def build(
        self,
        source_path: Path,
        output_path: Path,
        source_commit: str,
        repository_url: str = "unknown",
    ) -> ContextBundle:
        """
        Build and export a Context Bundle.
        """
        raise NotImplementedError
