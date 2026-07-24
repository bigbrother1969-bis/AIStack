import json
from pathlib import Path

from aistack.contracts.bundle_exporter import BundleExporter
from aistack.contracts.context_bundle import ContextBundle


class JsonBundleExporter(BundleExporter):
    """
    Export ContextBundle as JSON.

    This exporter does not transform knowledge.
    It only serializes the governed bundle.
    """

    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:

        data = {
            "id": bundle.id,
            "title": bundle.title,
            "generated_at": bundle.generated_at.isoformat(),
            "source_commit": bundle.source_commit,
            "classification_version": (
                bundle.classification_version
            ),
            "criticality_version": (
                bundle.criticality_version
            ),
            "artifacts": [
                {
                    "id": artifact.id,
                    "title": artifact.title,
                    "domain": artifact.domain,
                    "semantic_type": artifact.semantic_type,
                    "criticality": artifact.criticality,
                    "source": artifact.source,
                    "content": artifact.content,
                }
                for artifact in bundle.artifacts
            ],
        }

        output_path.write_text(
            json.dumps(
                data,
                indent=2,
            ),
            encoding="utf-8",
        )

        return output_path
