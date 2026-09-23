"""
Package Manager — DefaultValidationEngine.
"""

from __future__ import annotations

from pathlib import Path

from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)
from aistack.package_manager.contracts.validation_finding import (
    ValidationFinding,
)
from aistack.package_manager.contracts.validation_result import (
    ValidationResult,
)
from aistack.package_manager.interfaces.validation_engine import (
    ValidationEngine,
)


class DefaultValidationEngine(ValidationEngine):
    """
    Validates one item at a time against three checks:

    1. the target file exists;
    2. when an anchor is declared, it matches exactly one line of the
       target file's current content — zero or several matches is a
       failure, never a guess at which line was meant (the same
       uniqueness discipline a text replacement requires);
    3. the proposed content is not already present verbatim in the
       target file — a duplicate is a conflict, not a no-op.

    A package is `accepted` only when every item passes every check —
    `ARCH-0013`: "the validation phase must precede integration," and
    a partially-valid package is not a validated one.
    """

    def validate(
        self,
        package: KnowledgePackage,
        repository_root: Path,
    ) -> ValidationResult:

        findings: list[ValidationFinding] = []

        for item in package.items:

            target = repository_root / item.target_path

            if not target.is_file():
                findings.append(
                    ValidationFinding(
                        target_path=item.target_path,
                        passed=False,
                        message="target file does not exist",
                    )
                )
                continue

            text = target.read_text(encoding="utf-8")

            if item.content in text:
                findings.append(
                    ValidationFinding(
                        target_path=item.target_path,
                        passed=False,
                        message=(
                            "content already present in the target "
                            "file (duplicate)"
                        ),
                    )
                )
                continue

            if item.anchor is not None:

                lines = text.splitlines()

                occurrences = sum(
                    1 for line in lines if line == item.anchor
                )

                if occurrences == 0:
                    findings.append(
                        ValidationFinding(
                            target_path=item.target_path,
                            passed=False,
                            message=(
                                f"anchor {item.anchor!r} not found "
                                "as an exact line"
                            ),
                        )
                    )
                    continue

                if occurrences > 1:
                    findings.append(
                        ValidationFinding(
                            target_path=item.target_path,
                            passed=False,
                            message=(
                                f"anchor {item.anchor!r} is ambiguous "
                                f"({occurrences} exact-line matches)"
                            ),
                        )
                    )
                    continue

            findings.append(
                ValidationFinding(
                    target_path=item.target_path,
                    passed=True,
                    message="ready to integrate",
                )
            )

        accepted = all(finding.passed for finding in findings)

        return ValidationResult(
            package_id=package.package_id,
            accepted=accepted,
            findings=tuple(findings),
        )
