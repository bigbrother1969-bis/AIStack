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
    """

    def build(
        self,
        registry: KnowledgeRegistry,
        source_commit: str,
    ) -> ContextBundle:

        now = datetime.now()

        return ContextBundle(
            id=f"aistack-context-{now.date()}",
            title="AIStack Context Bundle",
            generated_at=now,
            source_commit=source_commit,
            artifacts=list(registry.artifacts),
            classification_version="1.0",
            criticality_version="1.0",
        )
