from abc import ABC, abstractmethod
from pathlib import Path

from aistack.contracts.context_bundle import ContextBundle


class BundleExportManager(ABC):
    """
    Contract for managing Context Bundle exports.
    """

    @abstractmethod
    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:
        """
        Export a complete portable bundle.
        """
        raise NotImplementedError
