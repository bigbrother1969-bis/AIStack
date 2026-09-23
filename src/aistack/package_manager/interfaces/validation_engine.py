"""
Package Manager — ValidationEngine interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.validation_result import (
    ValidationResult,
)


class ValidationEngine(ABC):
    """
    Contract for validating a GovernanceProposal against the governed
    heritage.

    `ARCH-0013`, verbatim: "A ValidationEngine is a governance
    component responsible for evaluating whether a proposed knowledge
    integration satisfies defined policies and constraints. A
    ValidationEngine does not perform integration."

    The policy this first implementation checks (see
    `DefaultValidationEngine`) is deliberately narrow: existence,
    anchor uniqueness, and duplicate content. `ARCH-0013`'s own Open
    Points leave "validation policies" and "integration conflict
    resolution rules" undecided — this does not resolve them in the
    abstract, it states plainly which three checks this first case
    needed and leaves the rest open rather than invented.
    """

    @abstractmethod
    def validate(
        self,
        proposal: GovernanceProposal,
        repository_root: Path,
    ) -> ValidationResult:
        """
        Evaluate every item of a proposal and report one finding each.
        """

        raise NotImplementedError
