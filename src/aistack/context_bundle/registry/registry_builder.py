from aistack.contracts.artifact_builder import ArtifactBuilder
from aistack.contracts.discovery import DiscoveryResult
from aistack.contracts.knowledge_registry import KnowledgeRegistry
from aistack.contracts.registry_builder import RegistryBuilder


class DefaultRegistryBuilder(RegistryBuilder):
    """
    Build a KnowledgeRegistry from discovered sources.

    This component only orchestrates artifact creation and registration.
    """


    def __init__(
        self,
        artifact_builder: ArtifactBuilder,
    ):
        self.artifact_builder = artifact_builder


    def build(
        self,
        discoveries: list[DiscoveryResult],
    ) -> KnowledgeRegistry:

        registry = KnowledgeRegistry()

        for discovery in discoveries:

            artifact = self.artifact_builder.build(
                discovery
            )

            registry.add(artifact)

        return registry
