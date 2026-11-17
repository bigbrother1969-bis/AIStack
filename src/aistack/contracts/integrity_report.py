from dataclasses import dataclass, field

from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


@dataclass(frozen=True)
class KnowledgeIntegrityReport:
    """
    Result of evaluating a Context Bundle against the
    integrity checks.

    The report carries the provenance of what was checked so
    that a finding can never be attributed to the wrong
    bundle.
    """

    bundle_id: str
    source_commit: str
    artifact_count: int
    findings: tuple[IntegrityFinding, ...] = field(
        default_factory=tuple
    )

    def of_severity(
        self,
        severity: IntegritySeverity,
    ) -> tuple[IntegrityFinding, ...]:

        return tuple(
            finding
            for finding in self.findings
            if finding.severity is severity
        )

    @property
    def blocking(self) -> tuple[IntegrityFinding, ...]:
        return self.of_severity(
            IntegritySeverity.BLOCKING
        )

    @property
    def warnings(self) -> tuple[IntegrityFinding, ...]:
        return self.of_severity(
            IntegritySeverity.WARNING
        )

    @property
    def is_clean(self) -> bool:
        """
        True when nothing blocking and nothing warned.

        Observations do not make a heritage unclean: they
        state facts that are not yet governed rules.
        """

        return not self.blocking and not self.warnings
