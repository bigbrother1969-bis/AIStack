from pathlib import Path

from aistack.contracts.bundle_exporter import BundleExporter
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.undeclared import UNDECLARED


def _heading(artifact) -> str:
    """
    A readable heading, without inventing a title.

    An artifact that declares no title carries UNDECLARED in the
    contract — that is the governed state and the validator
    reports it. Rendering forty-six "unknown" headings would
    make the projection unreadable, so the heading falls back to
    the source path: an observation the artifact already
    carries, presented as what it is.

    This is a presentation choice. Nothing here writes back into
    the artifact.
    """

    if artifact.title != UNDECLARED:
        return artifact.title

    return artifact.source


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
                    f"## {_heading(artifact)}",
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
