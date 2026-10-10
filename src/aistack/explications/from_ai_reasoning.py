"""
Import the AI Runtime's `explain` answers, as persisted by
`aistack.ai_runtime.reasoning_history`, as Explications (`ADR-0011`
§ 8).

AI Reasoning History is subject-keyed
(`reports/generated/ai-reasoning/<subject>.json`), so
`project_observation_history`'s generic scan never finds it; this
importer is its path into the graph.

Idempotent: an answer is skipped when an Explication for the same
subject already carries its instant in `metadata["source_instant"]`.
The files on disk are the only ledger.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aistack.history.subject_names import subject_for_stem
from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications.store import (
    DEFAULT_OUTPUT_DIR,
    read_explication_history,
    record_explication,
)
from aistack.history import available_stems, format_instant, latest_observations

DEFAULT_AI_REASONING_DIR = Path("reports/generated/ai-reasoning")


@dataclass(frozen=True)
class ExplainImportSummary:
    """What one `import_explain_answers` run actually did."""

    subjects_seen: int
    explain_answers_seen: int
    explications_recorded: int
    explications_already_imported: int


def import_explain_answers(
    ai_reasoning_dir: Path = DEFAULT_AI_REASONING_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ExplainImportSummary:
    """
    Record each `explain` answer in AI Reasoning History that is not
    already an Explication (by source instant) as a `Proposed`
    `KnowledgeArtifact` (`ADR-0011` § 7).
    """

    subjects_seen = 0
    explain_answers_seen = 0
    explications_recorded = 0
    explications_already_imported = 0

    for stem in available_stems(ai_reasoning_dir):
        subject = subject_for_stem(stem)
        subjects_seen += 1
        already_imported = {
            artifact.metadata.get("source_instant")
            for artifact in read_explication_history(subject, output_dir)
            if artifact.metadata.get("source_stream") == "ai-reasoning"
        }

        for observation in latest_observations(ai_reasoning_dir, stem):
            instant = observation.observed_at

            data = json.loads(observation.read())
            instant_label = format_instant(instant)

            for answer in data.get("answers", []):
                if answer.get("operation") != "explain":
                    continue

                explain_answers_seen += 1

                if instant_label in already_imported:
                    explications_already_imported += 1
                    continue

                artifact = KnowledgeArtifact(
                    id=subject,
                    title=f"Explication : {subject}",
                    declared_type="Explication",
                    domain=UNDECLARED,
                    semantic_type=UNDECLARED,
                    criticality=UNDECLARED,
                    owner=UNDECLARED,
                    source=f"model:{answer.get('model', UNDECLARED)}",
                    created_at=instant,
                    updated_at=instant,
                    confidence="Proposed",
                    status=UNDECLARED,
                    content=answer.get("response", ""),
                    metadata={
                        "source_stream": "ai-reasoning",
                        "source_instant": instant_label,
                        "explication_status": "Proposed",
                    },
                )
                record_explication(artifact, output_dir=output_dir)
                explications_recorded += 1

    return ExplainImportSummary(
        subjects_seen=subjects_seen,
        explain_answers_seen=explain_answers_seen,
        explications_recorded=explications_recorded,
        explications_already_imported=explications_already_imported,
    )
