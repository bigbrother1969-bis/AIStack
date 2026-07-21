"""
Knowledge Transaction - Operation Registry contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .operation_engine import OperationEngine


class OperationRegistry(ABC):
    """
    Registry of operation engines.
    """

    @abstractmethod
    def get(self, operation_type: str) -> OperationEngine:
        """
        Return the engine responsible for the given operation type.
        """
        raise NotImplementedError
