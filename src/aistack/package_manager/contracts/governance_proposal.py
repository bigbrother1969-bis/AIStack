"""
Package Manager — GovernanceProposal contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.package_manager.contracts.proposal_item import ProposalItem


@dataclass(frozen=True, slots=True)
class GovernanceProposal:
    """
    A set of proposed changes to the governed heritage — `FDN-0002`'s
    Governance Proposal: *"a proposed change generated from analysis or
    validation workflows"*, which *"requires appropriate validation
    before becoming governed knowledge."*

    A GovernanceProposal is not a Single Point Of Truth. It carries a
    proposed change to the receiving dock (`PackageManager`); the
    repository remains the SPOT once the change is integrated.

    It is not a KnowledgePackage either. The Context Bundle is the
    Knowledge Package of AIStack (`FDN-0002`); this carries a few
    proposed edits, one `ProposalItem` each, and is validated one item
    at a time.
    """

    proposal_id: str

    title: str

    source: str

    items: tuple[ProposalItem, ...]
