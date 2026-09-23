import pytest

from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)
from aistack.package_manager.contracts.proposal_item import ProposalItem
from aistack.package_manager.integration_engine import (
    DefaultIntegrationEngine,
)
from aistack.package_manager.manager import DefaultPackageManager
from aistack.package_manager.validation_engine import (
    DefaultValidationEngine,
)


def test_receive_validate_integrate_happy_path(tmp_path):
    """
    The whole quai de reception, exercised once end to end:
    Creation (built here) -> Receive -> Inspect -> Validate ->
    Integrate, matching ARCH-0013's lifecycle for the checks this
    first implementation covers.
    """

    target = tmp_path / "doc.md"
    target.write_text(
        "# Title\n\n## Section\n\nBody.\n",
        encoding="utf-8",
    )

    proposal = GovernanceProposal(
        proposal_id="proposal-happy",
        title="Test proposal",
        source="unit test",
        items=(
            ProposalItem(
                target_path="doc.md",
                content="New paragraph.",
                rationale="test",
                anchor="## Section",
                position="after",
            ),
        ),
    )

    manager = DefaultPackageManager()
    validator = DefaultValidationEngine()
    integrator = DefaultIntegrationEngine()

    received = manager.receive(proposal)

    notes = manager.inspect(received, tmp_path)
    assert "found 1 time(s)" in notes[0]

    validation = validator.validate(received, tmp_path)
    assert validation.accepted is True

    result = integrator.integrate(received, validation, tmp_path)

    assert result.applied is True
    assert "New paragraph." in target.read_text(encoding="utf-8")


def test_rejected_proposal_never_reaches_integration(tmp_path):

    proposal = GovernanceProposal(
        proposal_id="proposal-rejected",
        title="Test proposal",
        source="unit test",
        items=(
            ProposalItem(
                target_path="missing.md",
                content="New paragraph.",
                rationale="test",
            ),
        ),
    )

    manager = DefaultPackageManager()
    validator = DefaultValidationEngine()
    integrator = DefaultIntegrationEngine()

    received = manager.receive(proposal)

    validation = validator.validate(received, tmp_path)
    assert validation.accepted is False

    with pytest.raises(ValueError):
        integrator.integrate(received, validation, tmp_path)
