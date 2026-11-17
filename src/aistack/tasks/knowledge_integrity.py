from __future__ import annotations

from pathlib import Path

from aistack.integrity.bundle_reader import read_bundle
from aistack.integrity.engine import DefaultKnowledgeIntegrityEngine
from aistack.kernel.execution import Observation, ObservationContext, Request

DEFAULT_BUNDLE = "context/bundles/AIStack-Context-Bundle.zip"


class KnowledgeIntegrityTask:
    """
    Check a Context Bundle against the integrity checks
    (`knowledge.integrity`, `ADR-0027` § 13).

    The eighth chain the Runtime executes. It reads a published projection,
    the archive or the `bundle.json` it holds, and returns what each check
    observed: a finding states what was seen and on which subjects, and
    proposes nothing. It writes nothing; printing the report and the exit
    code are the command's.

    The request payload's `bundle` is the path of the projection (default
    `context/bundles/AIStack-Context-Bundle.zip`).
    """

    task_id = "knowledge.integrity"
    task_name = "Knowledge integrity"

    def execute(self, request: Request) -> Observation:
        path = Path(request.payload.get("bundle", DEFAULT_BUNDLE))
        report = DefaultKnowledgeIntegrityEngine().evaluate(read_bundle(path))

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "bundle": str(path),
                "bundle_id": report.bundle_id,
                "source_commit": report.source_commit,
                "artifact_count": report.artifact_count,
                "findings": [
                    {
                        "check": finding.check,
                        "severity": finding.severity.value,
                        "summary": finding.summary,
                        "affected": finding.affected,
                        "total": finding.total,
                        "unit": finding.unit,
                        "subjects": list(finding.subjects),
                    }
                    for finding in report.findings
                ],
                "blocking": len(report.blocking),
                "warnings": len(report.warnings),
                "clean": report.is_clean,
            },
        )
