"""
Import the AI Runtime's own `explain` answers as Explications —
`ADR-0011` § *Decision* 8's first real source: "already collected...
already kept since J7", so this module writes no new collector, only
a transform from what `aistack.ai_runtime.reasoning_history` already
persists into `aistack.explications`' own store.

**A real, previously uncaught gap this module's own reading depends
on, not one it repeats.** `aistack.ai_runtime.reasoning_history`
writes one JSON file per subject under
`reports/generated/ai-reasoning/<subject>.json`, with its own
timestamped history at `reports/generated/ai-reasoning/history/
<subject>/` — a subject-keyed layout, exactly like `aistack.
explications.store`'s own (see that module's comment on the same
shape, corrected before this patch). `aistack.timemachine.projection
.project_observation_history` only ever scans `generated_dir/
history/<stem>/` directly, so it has never actually found AI
Reasoning History there, despite `ADR-0011` § *Context*'s own table
having claimed it does — measured while building this importer, not
assumed from that table. Reshaping `project_observation_history`'s
generic scan to also discover a nested, subject-keyed stream would be
new scope this patch does not need: this importer already gives AI
Reasoning History's `explain` answers their own real path into the
graph, through Explications, which is the concern this ADR actually
opened. `ADR-0011` § *Context* is corrected alongside this patch to
say so plainly, rather than leave a claim standing that direct
measurement does not support.

**Idempotent by construction, not by a separate ledger.** Every
`explain` answer already carries the instant `aistack.ai_runtime
.reasoning_history` recorded it at; before importing one, this module
reads every Explication already recorded for that subject
(`aistack.explications.read_explication_history`) and skips any whose
own `metadata["source_instant"]` already matches — the files already
on disk are the ledger, the same principle `next_version_from_history`
already applies for versioning itself. Running this importer twice in
a row against unchanged AI Reasoning History records nothing new the
second time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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
    Walk every subject AI Reasoning History currently holds, find
    every `explain` answer recorded for it, and record each one that
    is not already an Explication (by source instant) as a `Proposed`
    `KnowledgeArtifact` (`ADR-0011` § 7).
    """

    subjects_seen = 0
    explain_answers_seen = 0
    explications_recorded = 0
    explications_already_imported = 0

    for subject in available_stems(ai_reasoning_dir):
        subjects_seen += 1
        already_imported = {
            artifact.metadata.get("source_instant")
            for artifact in read_explication_history(subject, output_dir)
            if artifact.metadata.get("source_stream") == "ai-reasoning"
        }

        for observation in latest_observations(ai_reasoning_dir, subject):
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
