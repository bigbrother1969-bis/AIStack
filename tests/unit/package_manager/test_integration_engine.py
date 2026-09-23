import pytest

from aistack.package_manager.contracts.integration_result import (
    IntegrationResult,
)
from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.proposal_item import ProposalItem
from aistack.package_manager.contracts.validation_finding import (
    ValidationFinding,
)
from aistack.package_manager.contracts.validation_result import (
    ValidationResult,
)
from aistack.package_manager.integration_engine import (
    DefaultIntegrationEngine,
)


def _proposal(items: tuple[ProposalItem, ...]) -> GovernanceProposal:

    return GovernanceProposal(
        proposal_id="proposal-test",
        title="Test proposal",
        source="unit test",
        items=items,
    )


def _accepted(proposal_id: str) -> ValidationResult:

    return ValidationResult(
        proposal_id=proposal_id,
        accepted=True,
        findings=(
            ValidationFinding(
                target_path="doc.md",
                passed=True,
                message="ready to integrate",
            ),
        ),
    )


def _rejected(proposal_id: str) -> ValidationResult:

    return ValidationResult(
        proposal_id=proposal_id,
        accepted=False,
        findings=(
            ValidationFinding(
                target_path="doc.md",
                passed=False,
                message="target file does not exist",
            ),
        ),
    )


def test_refuses_a_rejected_validation_result(tmp_path):

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    with pytest.raises(ValueError):
        DefaultIntegrationEngine().integrate(
            proposal,
            _rejected("proposal-test"),
            tmp_path,
        )


def test_refuses_a_validation_result_for_another_proposal(tmp_path):

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    with pytest.raises(ValueError):
        DefaultIntegrationEngine().integrate(
            proposal,
            _accepted("some-other-package"),
            tmp_path,
        )


def test_inserts_content_after_anchor(tmp_path):

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
                position="after",
            ),
        )
    )

    result = DefaultIntegrationEngine().integrate(
        proposal,
        _accepted("proposal-test"),
        tmp_path,
    )

    assert isinstance(result, IntegrationResult)
    assert result.applied is True
    assert result.changed_paths == ("doc.md",)

    new_text = target.read_text(encoding="utf-8")

    assert new_text.index("## Section") < new_text.index(
        "New paragraph."
    )
    assert new_text.index("New paragraph.") < new_text.index("Body.")


def test_inserts_content_before_anchor(tmp_path):

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
                position="before",
            ),
        )
    )

    DefaultIntegrationEngine().integrate(
        proposal,
        _accepted("proposal-test"),
        tmp_path,
    )

    new_text = target.read_text(encoding="utf-8")

    assert new_text.index("New paragraph.") < new_text.index(
        "## Section"
    )


def test_appends_content_when_anchor_is_none(tmp_path):

    target = tmp_path / "doc.md"
    target.write_text("# Title\n\nBody.\n", encoding="utf-8")

    proposal = _proposal(
        (
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
            ),
        )
    )

    DefaultIntegrationEngine().integrate(
        proposal,
        _accepted("proposal-test"),
        tmp_path,
    )

    new_text = target.read_text(encoding="utf-8")

    assert new_text.endswith("New paragraph.\n\n")
    assert new_text.index("Body.") < new_text.index("New paragraph.")


def test_rejected_result_leaves_the_file_untouched(tmp_path):

    target = tmp_path / "doc.md"
    original = "# Title\n\n## Section\n\nBody.\n"
    target.write_text(original, encoding="utf-8")

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

    with pytest.raises(ValueError):
        DefaultIntegrationEngine().integrate(
            proposal,
            _rejected("proposal-test"),
            tmp_path,
        )

    assert target.read_text(encoding="utf-8") == original
