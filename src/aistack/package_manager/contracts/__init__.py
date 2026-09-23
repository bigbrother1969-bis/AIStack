"""
Contracts for the Package Manager.
"""

from aistack.package_manager.contracts.integration_result import (
    IntegrationResult,
)
from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.proposal_item import (
    ProposalItem,
)
from aistack.package_manager.contracts.validation_finding import (
    ValidationFinding,
)
from aistack.package_manager.contracts.validation_result import (
    ValidationResult,
)

__all__ = [
    "IntegrationResult",
    "GovernanceProposal",
    "ProposalItem",
    "ValidationFinding",
    "ValidationResult",
]
