from datetime import datetime

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.context_bundle_builder import (
    ContextBundleBuilder,
)
from aistack.contracts.knowledge_registry import (
    KnowledgeRegistry,
)


class DefaultContextBundleBuilder(ContextBundleBuilder):
    """
    Build a ContextBundle from a governed KnowledgeRegistry.

    `measure_contracts` is a callable returning the contract
    architecture of the running package, or `None`. It is
    injected rather than called directly for two reasons.

    A bundle is a projection of the governed *knowledge*;
    measuring the *code* is a further capability the caller asks
    for, and a caller with no source tree to walk should not be
    forced to pretend otherwise — the resulting bundle then
    carries `None`, which FDN-0003 Article 12 makes a state
    rather than a zero.

    And it keeps the suite honest about its cost: walking 298
    modules takes 0.2 s, which is nothing once and something
    across every test that builds a bundle.
    """

    def __init__(self, measure_contracts=None) -> None:
        self.measure_contracts = measure_contracts

    def build(
        self,
        registry: KnowledgeRegistry,
        source_commit: str,
        repository_url: str = "unknown",
    ) -> ContextBundle:

        now = datetime.now()

        return ContextBundle(
            id=f"aistack-context-{now.date()}",
            title="AIStack Context Bundle",
            generated_at=now,
            source_commit=source_commit,
            repository_url=repository_url,
            artifacts=list(registry.artifacts),
            classification_version="1.0",
            criticality_version="1.0",
            contract_inventory=(
                self.measure_contracts()
                if self.measure_contracts
                else None
            ),
        )
