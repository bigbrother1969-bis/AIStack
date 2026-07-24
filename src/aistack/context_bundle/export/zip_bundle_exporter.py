from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from aistack.contracts.bundle_exporter import BundleExporter
from aistack.contracts.context_bundle import ContextBundle

from aistack.context_bundle.export.bundle_exporter import (
    JsonBundleExporter,
)

from aistack.context_bundle.export.markdown_bundle_exporter import (
    MarkdownBundleExporter,
)


class ZipBundleExporter(BundleExporter):
    """
    Export a ContextBundle as a portable ZIP archive.

    The ZIP contains derived representations only.
    """

    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:

        with TemporaryDirectory() as tmp:

            temp = Path(tmp)

            json_file = (
                temp / "bundle.json"
            )

            markdown_file = (
                temp / "bundle.md"
            )


            JsonBundleExporter().export(
                bundle,
                json_file,
            )

            MarkdownBundleExporter().export(
                bundle,
                markdown_file,
            )


            with zipfile.ZipFile(
                output_path,
                "w",
                zipfile.ZIP_DEFLATED,
            ) as archive:

                archive.write(
                    json_file,
                    "bundle.json",
                )

                archive.write(
                    markdown_file,
                    "bundle.md",
                )


        return output_path
