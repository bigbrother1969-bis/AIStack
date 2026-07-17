"""Evidence Collector interfaces."""

from abc import ABC, abstractmethod

from .interfaces import EvidenceItem


class EvidenceCollector(ABC):
    """Acquire immutable evidence from reality."""

    @abstractmethod
    def acquire(self) -> list[EvidenceItem]:
        """Acquire evidence."""
