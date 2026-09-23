from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.proposal_item import ProposalItem


def test_package_item_defaults():

    item = ProposalItem(
        target_path="docs/example.md",
        content="New paragraph.",
        rationale="test",
    )

    assert item.anchor is None
    assert item.position == "after"


def test_governance_proposal_carries_its_items():

    item = ProposalItem(
        target_path="docs/example.md",
        content="New paragraph.",
        rationale="test",
        anchor="## Heading",
        position="before",
    )

    proposal = GovernanceProposal(
        proposal_id="proposal-test",
        title="Test proposal",
        source="unit test",
        items=(item,),
    )

    assert proposal.proposal_id == "proposal-test"
    assert proposal.items == (item,)
    assert proposal.items[0].anchor == "## Heading"


def test_the_receiving_dock_declares_no_knowledge_package():
    """
    `FDN-0002`: the Context Bundle is the Knowledge Package of AIStack.
    What the PackageManager receives is a Governance Proposal, and the
    two names shall not be confused again (`GOV-0002/OS-060`).
    """

    import aistack.package_manager.contracts as contracts

    assert "KnowledgePackage" not in contracts.__all__
    assert not hasattr(contracts, "KnowledgePackage")
