import pytest

from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.proposal_item import ProposalItem
from aistack.package_manager.manager import DefaultPackageManager


def _proposal(
    proposal_id: str = "proposal-test",
    items: tuple[ProposalItem, ...] | None = None,
) -> GovernanceProposal:

    if items is None:
        items = (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
            ),
        )

    return GovernanceProposal(
        proposal_id=proposal_id,
        title="Test proposal",
        source="unit test",
        items=items,
    )


def test_receive_returns_a_well_formed_proposal():

    proposal = _proposal()

    received = DefaultPackageManager().receive(proposal)

    assert received is proposal


def test_receive_rejects_missing_proposal_id():

    proposal = _proposal(proposal_id="")

    with pytest.raises(ValueError):
        DefaultPackageManager().receive(proposal)


def test_receive_rejects_empty_items():

    proposal = _proposal(items=())

    with pytest.raises(ValueError):
        DefaultPackageManager().receive(proposal)


def test_receive_rejects_item_with_empty_target_path():

    proposal = _proposal(
        items=(
            ProposalItem(
                target_path="",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    with pytest.raises(ValueError):
        DefaultPackageManager().receive(proposal)


def test_inspect_reports_missing_target_file(tmp_path):

    proposal = _proposal(
        items=(
            ProposalItem(
                target_path="missing.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    notes = DefaultPackageManager().inspect(proposal, tmp_path)

    assert len(notes) == 1
    assert "missing.md" in notes[0]
    assert "does not exist" in notes[0]


def test_inspect_counts_anchor_occurrences(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    proposal = _proposal(
        items=(
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    notes = DefaultPackageManager().inspect(proposal, tmp_path)

    assert "found 1 time(s)" in notes[0]
