"""
Package Manager — PackageManager interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from aistack.package_manager.contracts.governance_proposal import (
    GovernanceProposal,
)


class PackageManager(ABC):
    """
    Contract for the receiving dock of a GovernanceProposal.

    `ARCH-0013`, verbatim: "The PackageManager coordinates knowledge
    package operations. Responsibilities: Receive Knowledge Packages.
    Inspect package content. Resolve available capabilities.
    Orchestrate validation and integration workflows. The
    PackageManager does not replace governance decisions."

    What this interface receives is a Governance Proposal (`FDN-0002`),
    not a Knowledge Package — the Context Bundle is the Knowledge
    Package of AIStack, and receiving one is not built.

    This interface covers the first two responsibilities only —
    receive and inspect. Resolving capabilities and orchestrating the
    validation/integration workflow is left to the caller, rather than
    building a generic orchestrator ahead of a second real case to
    generalize from. The first real orchestration was a one-off script
    run on 2026-09-23 (`87febe3`), removed with `GOV-0002/OS-060`.
    """

    @abstractmethod
    def receive(
        self,
        proposal: GovernanceProposal,
    ) -> GovernanceProposal:
        """
        Accept a GovernanceProposal as structurally well-formed.

        Raises `ValueError` if the proposal is malformed (no items, or
        an item with an empty target path or content) — a malformed
        proposal is rejected before it is ever inspected, not silently
        tolerated.
        """

        raise NotImplementedError

    @abstractmethod
    def inspect(
        self,
        proposal: GovernanceProposal,
        repository_root: Path,
    ) -> tuple[str, ...]:
        """
        Observe each item against the repository, without judgment.

        Returns one human-readable note per item: whether its target
        file exists, and how many times its anchor (if any) occurs.
        Inspection reports facts; whether those facts make the proposal
        acceptable is `ValidationEngine`'s responsibility, not this
        one's — `ARCH-0013` keeps the two separate.
        """

        raise NotImplementedError
