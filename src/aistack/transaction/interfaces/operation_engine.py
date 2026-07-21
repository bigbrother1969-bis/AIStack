"""
Knowledge Transaction - Operation Engine contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class OperationEngine(ABC):
    """
    Executes a governed operation payload.
    """

    @abstractmethod
    def execute(self, payload: object) -> object:
        """
        Execute the given payload and return the operation result.
        """
        raise NotImplementedError
