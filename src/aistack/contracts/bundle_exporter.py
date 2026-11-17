from abc import ABC, abstractmethod
from pathlib import Path

from aistack.contracts.context_bundle import ContextBundle


class BundleExporter(ABC):
    """
    Contract for exporting a governed Context Bundle.

    Export only serializes an already built knowledge context.
    """

    @abstractmethod
    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:
        """
        Export a Context Bundle to a portable artifact.
        """
        raise NotImplementedError
