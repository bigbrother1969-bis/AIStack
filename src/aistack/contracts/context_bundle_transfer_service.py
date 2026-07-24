from abc import ABC, abstractmethod
from pathlib import Path


class ContextBundleTransferService(ABC):
    """
    Contract for Context Bundle propagation.

    This service orchestrates transfer policy
    and transfer execution.
    """

    @abstractmethod
    def transfer(
        self,
        bundle_path: Path,
    ) -> bool:
        """
        Transfer a generated Context Bundle.

        Returns:
            True when transfer succeeds.
        """
        pass
