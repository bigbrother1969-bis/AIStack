"""
Package Manager — IntegrationEngine interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from aistack.package_manager.contracts.integration_result import (
    IntegrationResult,
)
from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.validation_result import (
    ValidationResult,
)


class IntegrationEngine(ABC):
    """
    Contract for applying a validated GovernanceProposal to the working
    tree.

    `ARCH-0013`, verbatim: "An IntegrationEngine is a governance
    component responsible for applying validated knowledge changes.
    Validation and integration remain separate responsibilities."

    `integrate` takes the `ValidationResult` explicitly rather than
    re-validating — an `IntegrationEngine` given a rejected
    `ValidationResult` must refuse (`ValueError`), never re-derive its
    own opinion of whether the proposal was acceptable.
    """

    @abstractmethod
    def integrate(
        self,
        proposal: GovernanceProposal,
        validation_result: ValidationResult,
        repository_root: Path,
    ) -> IntegrationResult:
        """
        Apply every item of an accepted proposal to its target file.

        Raises `ValueError` when `validation_result.accepted` is
        `False`, or when it does not carry the same `proposal_id`.
        """

        raise NotImplementedError
