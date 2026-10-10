from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.history.subject_names import stem_for_subject
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.generators.history import write_artifact_with_history
from aistack.kernel.time import Provenance, VersionId, next_version_from_history


# AI reasoning history: one stream per finding subject, one entry per finding
# combining all its operations (reason/explain/recommend). Recorded even when
# the engine was unreachable, since that is itself an outcome.
DEFAULT_OUTPUT_DIR = Path("reports/generated/ai-reasoning")


def reasoning_history_path(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> Path:
    """The stable "latest" path of one subject's reasoning history."""

    return output_dir / f"{stem_for_subject(subject)}.json"


def serialize_ai_reasoning(
    finding: RuntimeFinding,
    answers: tuple[AIRuntimeAnswer, ...],
    *,
    version: VersionId,
    provenance: Provenance,
) -> dict[str, Any]:
    """
    The JSON-safe shape of one reasoning history entry: the finding and every
    operation's full answer (prompt, response, model, reachability), so the
    reasoning can be read back without re-running the call.
    """

    return {
        "version": {
            "subject": version.subject,
            "sequence": version.sequence,
        },
        "provenance": {
            "origin": provenance.origin,
            "causality": provenance.causality,
        },
        "finding": {
            "subject": finding.subject,
            "signature": finding.signature,
            "interpretation": finding.interpretation,
            "remediation": finding.remediation,
            "confidence": finding.confidence,
            "qualifications": list(finding.qualifications),
        },
        "answers": [
            {
                "operation": answer.operation,
                "model": answer.model,
                "prompt": answer.prompt,
                "response": answer.response,
                "reachable": answer.reachable,
                "unreachable_reason": answer.unreachable_reason,
                "language": answer.language,
            }
            for answer in answers
        ],
    }


def record_ai_reasoning(
    finding: RuntimeFinding,
    answers: tuple[AIRuntimeAnswer, ...],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """
    Persist one finding's reasoning round to its subject's history stream
    and return the "latest" path written.

    `version` counts the subject's existing history on disk, so it survives
    process restarts. `provenance.causality` stays `None`: no request
    triggers a reasoning run.
    """

    path = reasoning_history_path(finding.subject, output_dir)
    version = next_version_from_history(path.parent, path.stem)
    provenance = Provenance(origin="aistack.cli.ai_reason")

    content = (
        json.dumps(
            serialize_ai_reasoning(
                finding, answers, version=version, provenance=provenance
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, path)

    return latest_path
