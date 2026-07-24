from abc import ABC, abstractmethod
from pathlib import Path

from aistack.contracts.context_bundle import ContextBundle


class ContextBundleService(ABC):
    """
    Application service for Context Bundle generation.
    """

    @abstractmethod
    def generate(
        self,
        source_path: Path,
        output_path: Path,
        source_commit: str,
    ) -> ContextBundle:
        """
        Generate a complete Context Bundle.
        """
        raise NotImplementedError
