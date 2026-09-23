"""
First real KnowledgePackage run through the Package Manager.

Fabricated deliberately as a real, small documentation change rather
than a synthetic fixture — same principle already applied for
`aistack-verif-0005` (a real CPU load rather than a simulated finding,
see `claude/SESSION-2026-09-18-open-points-closure.md`).

The package: `ARCH-0013-Knowledge-Package-Architecture.md` and
`ARCH-0009-Library-Architecture-Analogy.md` do not cite each other.
Today's session established their relationship (PackageManager is the
role this analogy calls the Logistics/Acquisition department; a Context
Bundle is one example of a KnowledgePackage, not a synonym for
PackageManager) — real, small, and not yet anywhere in the governed
heritage.

Usage:

    PYTHONPATH=src python3 scripts/apply_arch0009_arch0013_cross_reference.py

Dry run by default: receives, inspects, and validates the package, and
prints what would happen. Pass `--apply` to actually write the two
files. Review the result with `git diff` before `git add`/`git commit`
— that review is the Human Governance Validation step `ARCH-0013`'s own
flow places between ValidationEngine and IntegrationEngine.
"""

from __future__ import annotations

import sys
from pathlib import Path

from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)
from aistack.package_manager.contracts.package_item import PackageItem
from aistack.package_manager.integration_engine import (
    DefaultIntegrationEngine,
)
from aistack.package_manager.manager import DefaultPackageManager
from aistack.package_manager.validation_engine import (
    DefaultValidationEngine,
)

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

ARCH_0013_CONTENT = """# Relationship To The Library Architecture Analogy

`ARCH-0009` gives AIStack's shared mental model: a governed digital
library, where a Context Bundle is "the library packed for a move."

A KnowledgePackage is not a Context Bundle under another name.

A Context Bundle is one example of a KnowledgePackage: a package whose
content happens to be a complete projection of the governed heritage,
built and shipped by the Context Bundle Engine (`ADR-0005` to
`ADR-0007`). Other KnowledgePackages carry smaller, partial content.

The PackageManager plays the role `ARCH-0009` names but does not yet
build: the Logistics department (`TransportService`), extended on
arrival by what an Acquisition department (`KnowledgeService`) does in
a real library — check a delivery against the existing catalogue before
it is shelved. The Context Bundle Engine already builds and ships one
kind of package; it does not receive one.

------------------------------------------------------------------------"""

ARCH_0009_CONTENT = """## PackageManager Is a Complementary Role, Not a Synonym

`ARCH-0013` names a PackageManager: it receives a package, inspects it,
and orchestrates validation and integration before anything reaches the
governed heritage.

That role is this analogy's Logistics department (`TransportService`),
extended on arrival by what an Acquisition department
(`KnowledgeService`) does in a real library: check a delivery against
the existing catalogue before it is shelved. Neither is built yet.

A Context Bundle — "the library packed for a move," above — is a
KnowledgePackage, not a PackageManager. It is what a PackageManager
would receive, not what receives it."""


def build_package() -> KnowledgePackage:

    return KnowledgePackage(
        package_id="pkg-2026-09-23-packagemanager-contextbundle-crossref",
        title=(
            "Cross-reference ARCH-0013 and ARCH-0009 on the "
            "PackageManager/ContextBundle relationship"
        ),
        source="Cowork session, 2026-09-23",
        items=(
            PackageItem(
                target_path=(
                    "docs/01-architecture/concepts/"
                    "ARCH-0013-Knowledge-Package-Architecture.md"
                ),
                content=ARCH_0013_CONTENT,
                rationale=(
                    "ARCH-0013 does not cite ARCH-0009; the two "
                    "describe complementary concepts (PackageManager "
                    "vs. ContextBundle) without ever saying so."
                ),
                anchor="# Open Points",
                position="before",
            ),
            PackageItem(
                target_path=(
                    "docs/01-architecture/concepts/"
                    "ARCH-0009-Library-Architecture-Analogy.md"
                ),
                content=ARCH_0009_CONTENT,
                rationale=(
                    "ARCH-0009 names the Logistics/Acquisition "
                    "department roles but never connects them to "
                    "ARCH-0013's PackageManager."
                ),
                anchor="## Future evolution",
                position="before",
            ),
        ),
    )


def main() -> int:

    apply = "--apply" in sys.argv

    package = build_package()

    manager = DefaultPackageManager()
    validator = DefaultValidationEngine()
    integrator = DefaultIntegrationEngine()

    received = manager.receive(package)

    print(f"Received package: {received.package_id}")
    print()

    print("Inspection:")
    for note in manager.inspect(received, REPOSITORY_ROOT):
        print(f"  - {note}")
    print()

    result = validator.validate(received, REPOSITORY_ROOT)

    print(f"Validation accepted: {result.accepted}")
    for finding in result.findings:
        status = "PASS" if finding.passed else "FAIL"
        print(f"  [{status}] {finding.target_path}: {finding.message}")
    print()

    if not result.accepted:
        print("Not integrating: validation rejected the package.")
        return 1

    if not apply:
        print(
            "Dry run only — pass --apply to write the two files. "
            "Review with `git diff` before committing."
        )
        return 0

    integration = integrator.integrate(
        received,
        result,
        REPOSITORY_ROOT,
    )

    print(f"Integrated: {integration.applied}")
    for path in integration.changed_paths:
        print(f"  - changed: {path}")
    for note in integration.notes:
        print(f"  - {note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
