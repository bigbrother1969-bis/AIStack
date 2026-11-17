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
                    # Published so the fingerprint survives a
                    # round trip. A consumer that read the bundle
                    # back and recomputed the hash would otherwise
                    # get a different value from the one the
                    # manifest states.
                    "content_hash": artifact.metadata.get(
                        "content_hash", ""
                    ),
                    "title": artifact.title,
                    "type": artifact.declared_type,
                    "domain": artifact.domain,
                    "semantic_type": artifact.semantic_type,
                    "criticality": artifact.criticality,
                    "owner": artifact.owner,
                    "status": artifact.status,
                    "confidence": artifact.confidence,
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
