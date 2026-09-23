"""
Package Manager — ValidationResult contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.package_manager.contracts.validation_finding import (
    ValidationFinding,
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """
    The outcome of validating a whole GovernanceProposal.

    `accepted` is `True` only when every `ValidationFinding` passed.
    An `IntegrationEngine` that receives a `ValidationResult` with
    `accepted=False` must refuse to integrate — `ARCH-0013`'s
    ValidationEngine "does not perform integration", and its
    IntegrationEngine "applies validated changes", not proposed ones.
    """

    proposal_id: str

    accepted: bool

    findings: tuple[ValidationFinding, ...]
