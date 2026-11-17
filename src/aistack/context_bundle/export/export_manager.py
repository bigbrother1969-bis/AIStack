from pathlib import Path

from aistack.contracts.bundle_export_manager import (
    BundleExportManager,
)

from aistack.contracts.context_bundle import (
    ContextBundle,
)

from aistack.context_bundle.export.bundle_exporter import (
    JsonBundleExporter,
)

from aistack.context_bundle.export.markdown_bundle_exporter import (
    MarkdownBundleExporter,
)

from aistack.context_bundle.export.zip_bundle_exporter import (
    ZipBundleExporter,
)


class DefaultBundleExportManager(BundleExportManager):
    """
    Coordinate all Context Bundle exports.

    This component only delegates rendering.
    Knowledge is already built before export.
    """

    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:

        output_dir = output_path.parent

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        JsonBundleExporter().export(
            bundle,
            output_dir / "bundle.json",
        )

        MarkdownBundleExporter().export(
            bundle,
            output_dir / "bundle.md",
        )

        return ZipBundleExporter().export(
            bundle,
            output_path,
        )
