from pathlib import Path

from aistack.contracts.bundle_exporter import BundleExporter
from aistack.contracts.context_bundle import ContextBundle


class MarkdownBundleExporter(BundleExporter):
    """
    Export a ContextBundle as human-readable Markdown.

    This exporter only renders an existing bundle.
    """

    def export(
        self,
        bundle: ContextBundle,
        output_path: Path,
    ) -> Path:

        lines = [
            "# AIStack Context Bundle",
            "",
            f"ID: {bundle.id}",
            f"Generated: {bundle.generated_at.isoformat()}",
            f"Source commit: {bundle.source_commit}",
            "",
            "---",
            "",
        ]

        for artifact in bundle.artifacts:

            lines.extend(
                [
                    f"## {artifact.title}",
                    "",
                    f"- ID: {artifact.id}",
                    f"- Source: {artifact.source}",
                    f"- Type: {artifact.declared_type}",
                    f"- Domain: {artifact.domain}",
                    f"- Semantic type: {artifact.semantic_type}",
                    f"- Criticality: {artifact.criticality}",
                    f"- Owner: {artifact.owner}",
                    f"- Status: {artifact.status}",
                    f"- Confidence: {artifact.confidence}",
                    "",
                    artifact.content,
                    "",
                    "---",
                    "",
                ]
            )

        output_path.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        return output_path
