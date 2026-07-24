from pathlib import Path

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.context_bundle_engine import (
    ContextBundleEngine,
)

from aistack.context_bundle.discovery.markdown_discovery import (
    MarkdownDiscovery,
)

from aistack.context_bundle.builders.artifact_builder import (
    MarkdownArtifactBuilder,
)

from aistack.context_bundle.registry.registry_builder import (
    DefaultRegistryBuilder,
)

from aistack.context_bundle.generation.context_bundle_builder import (
    DefaultContextBundleBuilder,
)

from aistack.context_bundle.export.export_manager import (
    DefaultBundleExportManager,
)


class DefaultContextBundleEngine(ContextBundleEngine):
    """
    Default orchestration engine.

    This component only coordinates the pipeline.
    """

    def __init__(self):

        self.discovery = MarkdownDiscovery()

        self.registry_builder = (
            DefaultRegistryBuilder(
                MarkdownArtifactBuilder()
            )
        )

        self.bundle_builder = (
            DefaultContextBundleBuilder()
        )

        self.exporter = (
            DefaultBundleExportManager()
        )


    def build(
        self,
        source_path: Path,
        output_path: Path,
        source_commit: str,
    ) -> ContextBundle:

        discoveries = (
            self.discovery.discover(
                source_path
            )
        )

        registry = (
            self.registry_builder.build(
                discoveries
            )
        )

        bundle = (
            self.bundle_builder.build(
                registry,
                source_commit,
            )
        )

        self.exporter.export(
            bundle,
            output_path,
        )

        return bundle
