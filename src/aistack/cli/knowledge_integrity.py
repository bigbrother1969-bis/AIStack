from __future__ import annotations

from pathlib import Path
import sys

from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.bundle_reader import read_bundle
from aistack.integrity.engine import (
    DefaultKnowledgeIntegrityEngine,
)


DEFAULT_BUNDLE = Path(
    "context/bundles/AIStack-Context-Bundle.zip"
)


LABELS = {
    IntegritySeverity.BLOCKING: "BLOCKING",
    IntegritySeverity.WARNING: "WARNING",
    IntegritySeverity.OBSERVATION: "OBSERVED",
}


def main() -> None:

    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else DEFAULT_BUNDLE
    )

    if not target.exists():
        print(f"Bundle not found: {target}")
        raise SystemExit(2)

    bundle = read_bundle(target)

    report = DefaultKnowledgeIntegrityEngine().evaluate(
        bundle
    )

    print("Knowledge Integrity Report")
    print(f"- Bundle: {report.bundle_id}")
    print(f"- Source commit: {report.source_commit}")
    print(f"- Artifacts: {report.artifact_count}")
    print("")

    if not report.findings:
        print("No finding.")

    for finding in report.findings:

        print(
            f"[{LABELS[finding.severity]}] "
            f"{finding.check}: {finding.summary}"
        )

        print(
            f"    {finding.affected}/{finding.total} "
            f"{finding.unit}"
        )

    print("")
    print(
        f"blocking: {len(report.blocking)}   "
        f"warnings: {len(report.warnings)}   "
        f"clean: {report.is_clean}"
    )

    if report.blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
