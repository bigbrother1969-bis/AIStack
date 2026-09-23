"""
Package Manager — IntegrationResult contract.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IntegrationResult:
    """
    The outcome of integrating a validated GovernanceProposal.

    Integration updates the working tree only — it never commits,
    pushes, or archives on its own behalf. Making the resulting change
    part of the governed heritage remains a deliberate human act (a
    `git diff` review, then `git add`/`git commit`), the same
    Human Governance Validation step `ARCH-0013`'s flow places between
    ValidationEngine and IntegrationEngine, exercised here as the
    review before the commit rather than as a gate inside the code.
    """

    proposal_id: str

    applied: bool

    changed_paths: tuple[str, ...]

    notes: tuple[str, ...]
