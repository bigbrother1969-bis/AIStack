from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.generators.history import write_artifact_with_history
from aistack.kernel.time import Provenance, VersionId, next_version_from_history


# AI Reasoning History — J7, `claude/PLAN-TRAJECTOIRE-2026-09-04.md`,
# the fourth of the four orthogonal historisation flows the owner
# opened 2026-09-03 (`docs/99-meta/roadmap/AIStack-Medium-Term-
# Development-Roadmap.md` § *Multi-Orthogonal History Model*), and
# the last of the four still missing before this patch: `reason`/
# `explain`/`recommend` (J6, delivered 2026-09-13) already produce a
# full `AIRuntimeAnswer` per call — prompt, response, model,
# reachability — but `aistack.cli.ai_reason.main()` only ever printed
# it. Nothing survived the process.
#
# **Same model as the other three flows, not a fifth mechanism** —
# `claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`'s own conclusion
# ("un jalon qui aurait livré un cinquième mécanisme ad hoc... aurait
# répété exactement le problème qu'il est censé fermer") applies here
# unchanged: `VersionId`/`Provenance` from `aistack.kernel.time`,
# `write_artifact_with_history` for storage — the same two governed
# facts `aistack.kernel.tracing.repository.file.FileTraceRepository`
# and `aistack.priority.decision_history` already carry, not a new
# shape invented for this flow alone.
#
# **One stream per finding subject, not one shared stream** — decided
# with the owner 2026-09-18: `reports/generated/ai-reasoning/
# <subject>.json`, so `booklore_db`'s reasoning history and
# `frigate`'s stay independently versioned and queryable
# (`aistack.cli.history_query`), the same way Observation History
# already keeps one stream per provider rather than one file for
# every observation ever made.
#
# **One entry per finding, combining all three operations** — decided
# with the owner 2026-09-18: `reason`/`explain`/`recommend` are
# always called together for one finding (`ai_reason.main()`'s own
# loop), and `report()` already prints them as one block per finding.
# Splitting them into three independently-versioned entries would
# fragment what is already read, and written, as a single reasoning
# event.
#
# **Traced even when unreachable** — decided with the owner
# 2026-09-18: an `AIRuntimeAnswer` with `reachable=False` is still a
# real, complete outcome (`FDN-0003` Article 12 — the engine's own
# unreachability is a fact, not an absence to hide), so `record_ai_
# reasoning` is called unconditionally for every finding `ai_reason
# .main()` processes, never gated on whether any answer succeeded.
DEFAULT_OUTPUT_DIR = Path("reports/generated/ai-reasoning")


def reasoning_history_path(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> Path:
    """
    The stable "latest" path one finding's reasoning history is
    read from and written to — `output_dir/<subject>.json`, the
    same per-subject convention Observation History already uses
    per provider.
    """

    return output_dir / f"{subject}.json"


def serialize_ai_reasoning(
    finding: RuntimeFinding,
    answers: tuple[AIRuntimeAnswer, ...],
    *,
    version: VersionId,
    provenance: Provenance,
) -> dict[str, Any]:
    """
    The JSON-safe shape one AI Reasoning History entry is persisted
    as — the finding it was asked about, alongside every operation's
    full `AIRuntimeAnswer` (context provided, knowledge/rules cited
    via the finding, proposition generated, confidence — the five
    things `AIStack-Medium-Term-Development-Roadmap.md` § *4. AI
    Reasoning History* names), never collapsed to just the response
    text: "why did AIStack produce this recommendation" has to be
    answerable from this alone, without re-running the call.
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
    Persist one finding's full reasoning round (every operation
    `ai_reason.main()` ran against it) to its subject's own history
    stream. Returns the stable "latest" path written
    (`write_artifact_with_history`'s own convention).

    **`version`/`provenance` — J3, absorbed here as the fourth proof
    of life**, the same approach `FileTraceRepository.save()` and
    `decision_history.record_decision` already take:
    `next_version_from_history` counts this subject's own history
    already on disk rather than keeping a second, process-local
    counter that would restart at 1 on every CLI invocation.
    `provenance.origin` names the CLI that is this flow's only
    producer today; `causality` stays `None` — no `Request` triggers
    an `ai_reason` run, the same honest gap `decision_history`
    already names for its own monitor loop.
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
