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

from aistack.context_bundle.export.readme_bundle_exporter import (
    ReadmeBundleExporter,
)

from aistack.context_bundle.manifest.manifest_builder import (
    DefaultBundleManifest,
)

from aistack.context_bundle.manifest.json_serializer import (
    JsonManifestSerializer,
)

from aistack.context_bundle.manifest.content_hash import (
    HASH_ALGORITHM,
    compute_content_hash,
)


class ZipBundleExporter(BundleExporter):
    """
    Export a ContextBundle as a portable ZIP archive.

    The ZIP contains derived representations only:
    - README.md
    - bundle.json
    - bundle.md
    - manifest.json
    """

    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:

        with TemporaryDirectory() as tmp:

            temp = Path(tmp)

            json_file = temp / "bundle.json"

            markdown_file = temp / "bundle.md"

            manifest_file = temp / "manifest.json"


            JsonBundleExporter().export(
                bundle,
                json_file,
            )


            MarkdownBundleExporter().export(
                bundle,
                markdown_file,
            )


            manifest = DefaultBundleManifest(
                _bundle_id=bundle.id,
                _generated_at=(
                    bundle.generated_at.isoformat()
                ),
                _source_commit=bundle.source_commit,
                _artifact_count=len(
                    bundle.artifacts
                ),
                _repository_url=bundle.repository_url,
                _content_hash=compute_content_hash(
                    bundle.artifacts
                ),
                _hash_algorithm=HASH_ALGORITHM,
            )


            manifest_file.write_text(
                JsonManifestSerializer().serialize(
                    manifest
                ),
                encoding="utf-8",
            )


            readme_content = (
                ReadmeBundleExporter().export()
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

                archive.write(
                    manifest_file,
                    "manifest.json",
                )

                archive.writestr(
                    "README.md",
                    readme_content,
                )


        return output_path
