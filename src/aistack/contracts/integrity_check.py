from abc import ABC, abstractmethod

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_finding import IntegrityFinding


class IntegrityCheck(ABC):
    """
    Contract for a single knowledge integrity check.

    A check observes a Context Bundle and returns findings.
    It never modifies the bundle and never decides what to
    do about what it finds.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:
        raise NotImplementedError
