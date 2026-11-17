from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.contract_inventory import ContractInventory
from aistack.contracts.registry_inventory import RegistryInventory


@dataclass(frozen=True)
class ContextBundle:
    """
    Immutable representation of a complete AIStack knowledge context.

    A Context Bundle is a portable representation of the governed knowledge
    heritage.

    Classification and criticality do not filter artifacts.
    They define how AI systems interpret and use knowledge.
    """

    id: str

    title: str

    generated_at: datetime

    source_commit: str

    artifacts: list[KnowledgeArtifact] = field(default_factory=list)

    # Canonical location of the governance SPOT this bundle projects
    repository_url: str = "unknown"

    # Governance model versions used during generation
    classification_version: str = "1.0"
    criticality_version: str = "1.0"

    # The contract architecture measured at generation.
    #
    # FDN-0011 makes technical debt a property of the contracts
    # and requires it to be derived. Carrying the derivation in
    # the projection is what makes it *published* rather than
    # available to whoever thinks to run a command: an agent that
    # receives this bundle and nothing else can state the debt of
    # the heritage it was given.
    #
    # `None` means the bundle was produced without the
    # measurement, by an older pipeline or by a caller that had no
    # source tree to walk. It is a governed state under FDN-0003
    # Article 12, and a check that finds it says so rather than
    # reporting zero orphans.
    #
    # It is deliberately outside `content_hash`, which is derived
    # from artifact identities alone so that a bundle from a
    # mirror can be proven equivalent to one from the SPOT. This
    # inventory is a measurement of the code, not a governed
    # artifact — disposable under ENG-P-003 — and two bundles of
    # the same heritage built from different working trees are
    # still the same projection.
    contract_inventory: ContractInventory | None = None

    # What the Kernel registers at bootstrap, and what asks for
    # it, measured at generation.
    #
    # The second of the three dimensions GOV-0002/OS-001 named as
    # placing a contract — what implements it, what **consumes**
    # it, what governs it — for the one form of consumption the
    # Kernel makes explicit: a capability registered under an
    # identifier and resolved by that identifier. ADR-0004
    # § *Discovery Model* decides that form; nothing measured it
    # until 2026-08-28.
    #
    # `None`, and `measured` false inside it, carry the same
    # distinction as the contract inventory: a bundle produced
    # without the measurement is not a heritage in which nothing
    # is registered.
    #
    # Outside `content_hash` for the same reason: a measurement of
    # the code, not a governed artifact.
    registry_inventory: RegistryInventory | None = None

    # Generated output location
    output_path: Path | None = None
