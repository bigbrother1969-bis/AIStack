from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.proposal_item import ProposalItem
from aistack.package_manager.validation_engine import (
    DefaultValidationEngine,
)


def _proposal(items: tuple[ProposalItem, ...]) -> GovernanceProposal:

    return GovernanceProposal(
        proposal_id="proposal-test",
        title="Test proposal",
        source="unit test",
        items=items,
    )


def test_missing_target_file_is_rejected(tmp_path):

    proposal = _proposal(
        (
            ProposalItem(
                target_path="missing.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    result = DefaultValidationEngine().validate(proposal, tmp_path)

    assert result.accepted is False
    assert result.findings[0].passed is False
    assert "does not exist" in result.findings[0].message


def test_missing_anchor_is_rejected(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text("# Title\n\nBody.\n", encoding="utf-8")

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(proposal, tmp_path)

    assert result.accepted is False
    assert "not found" in result.findings[0].message


def test_ambiguous_anchor_is_rejected(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n\n## Section\n\nMore.\n",
        encoding="utf-8",
    )

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(proposal, tmp_path)

    assert result.accepted is False
    assert "ambiguous" in result.findings[0].message


def test_duplicate_content_is_rejected(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nAlready there.\n",
        encoding="utf-8",
    )

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="Already there.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(proposal, tmp_path)

    assert result.accepted is False
    assert "duplicate" in result.findings[0].message


def test_well_formed_item_is_accepted(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
        )
    )

    result = DefaultValidationEngine().validate(proposal, tmp_path)

    assert result.accepted is True
    assert result.findings[0].passed is True


def test_a_single_failing_item_rejects_the_whole_proposal(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
            ),
            ProposalItem(
                target_path="missing.md",
                content="Other paragraph.",
                rationale="test",
            ),
        )
    )

    result = DefaultValidationEngine().validate(proposal, tmp_path)

    assert result.accepted is False
    assert result.findings[0].passed is True
    assert result.findings[1].passed is False
