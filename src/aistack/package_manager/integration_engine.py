"""
Package Manager — DefaultIntegrationEngine.
"""

from __future__ import annotations

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
from aistack.package_manager.interfaces.integration_engine import (
    IntegrationEngine,
)


class DefaultIntegrationEngine(IntegrationEngine):
    """
    Applies every item of an accepted proposal to its target file.

    Refuses outright — no partial application, no file touched — when
    the `ValidationResult` was not accepted, or was computed for a
    different proposal. Integration never re-validates on its own.
    """

    def integrate(
        self,
        proposal: GovernanceProposal,
        validation_result: ValidationResult,
        repository_root: Path,
    ) -> IntegrationResult:

        if validation_result.proposal_id != proposal.proposal_id:
            raise ValueError(
                "validation_result was computed for a different "
                f"proposal ({validation_result.proposal_id!r} != "
                f"{proposal.proposal_id!r})"
            )

        if not validation_result.accepted:
            raise ValueError(
                f"proposal {proposal.proposal_id!r} was not accepted "
                "by validation; refusing to integrate"
            )

        changed_paths: list[str] = []
        notes: list[str] = []

        for item in proposal.items:

            target = repository_root / item.target_path

            text = target.read_text(encoding="utf-8")

            block = item.content.strip("\n") + "\n\n"

            if item.anchor is None:

                separator = "" if text.endswith("\n") else "\n"

                new_text = text + separator + "\n" + block

            else:

                lines = text.splitlines(keepends=True)

                index = next(
                    i
                    for i, line in enumerate(lines)
                    if line.rstrip("\n") == item.anchor
                )

                insert_at = (
                    index if item.position == "before" else index + 1
                )

                lines.insert(insert_at, block)

                new_text = "".join(lines)

            target.write_text(new_text, encoding="utf-8")

            changed_paths.append(item.target_path)

            notes.append(
                f"{item.target_path}: integrated ({item.rationale})"
            )

        return IntegrationResult(
            proposal_id=proposal.proposal_id,
            applied=True,
            changed_paths=tuple(changed_paths),
            notes=tuple(notes),
        )
