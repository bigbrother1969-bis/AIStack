from abc import ABC, abstractmethod
from pathlib import Path


class BundleTransfer(ABC):
    """
    Contract for transferring Context Bundle artifacts.

    A transfer implementation must:
    - transfer generated knowledge artifacts;
    - provide a validation result;
    - remain independent from bundle generation.
    """

    @abstractmethod
    def transfer(
        self,
        source: Path,
        target: str,
    ) -> bool:
        """
        Transfer a bundle artifact.

        Args:
            source:
                Path of generated bundle artifact.

            target:
                Destination identifier.

        Returns:
            True when transfer is validated.
        """
        pass
