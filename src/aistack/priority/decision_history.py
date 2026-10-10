from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aistack.generators.history import write_artifact_with_history
from aistack.kernel.time import Provenance, VersionId, next_version_from_history
from aistack.priority.apply import ApplyReport


# History of CPU priority decisions. Written only when `ApplyReport.changed`,
# not on every poll, to avoid thousands of identical entries a day. Records
# each app's boosted state and the apply report; detectors expose only
# `is_active()`, so the raw reading behind a decision is not available.
DEFAULT_OUTPUT_PATH = Path("reports/generated/resource-priority-decision.json")


def serialize_decision(
    boosted: Mapping[str, bool],
    report: ApplyReport,
    *,
    version: VersionId,
    provenance: Provenance,
) -> dict[str, Any]:
    """
    The JSON-safe shape one resource-priority decision is persisted as.

    The four report buckets are kept separate so a reader can tell "already
    correct", "changed", "gone" and "Docker refused" apart. There is no
    timestamp field: the history filename already records the instant.
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
        "boosted": dict(boosted),
        "applied": list(report.applied),
        "unchanged": list(report.unchanged),
        "not_found": list(report.not_found),
        "failed": [list(pair) for pair in report.failed],
        "dry_run": report.dry_run,
    }


def record_decision(
    boosted: Mapping[str, bool],
    report: ApplyReport,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path | None:
    """
    Persist one decision to history when `report.changed`; otherwise do
    nothing and return `None`. Returns the "latest" path written.

    `version` counts this subject's existing history under `output_path`'s
    directory. `provenance.causality` stays `None`: no request causes a CPU
    decision.
    """

    if not report.changed:
        return None

    version = next_version_from_history(output_path.parent, output_path.stem)
    provenance = Provenance(origin="aistack.priority.resource_priority_monitor")

    content = (
        json.dumps(
            serialize_decision(boosted, report, version=version, provenance=provenance),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, output_path)

    return latest_path
