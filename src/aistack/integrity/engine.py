from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_report import (
    KnowledgeIntegrityReport,
)

from aistack.integrity.checks.classification_coherence import (
    ClassificationCoherenceCheck,
)
from aistack.integrity.checks.classification_declaration import (
    ClassificationDeclarationCheck,
)
from aistack.integrity.checks.contract_debt import (
    ContractDebtCheck,
)
from aistack.integrity.checks.duplicate_titles import (
    DuplicateTitleCheck,
)
from aistack.integrity.checks.knowledge_state import (
    KnowledgeStateCheck,
)
from aistack.integrity.checks.metadata_completeness import (
    MetadataCompletenessCheck,
)
from aistack.integrity.checks.principle_identifiers import (
    PrincipleIdentifierCheck,
)
from aistack.integrity.checks.projection_fidelity import (
    ProjectionFidelityCheck,
)
from aistack.integrity.checks.register_coherence import (
    RegisterCoherenceCheck,
)
from aistack.integrity.checks.reference_integrity import (
    ReferenceIntegrityCheck,
)
from aistack.integrity.checks.structural_integrity import (
    StructuralIntegrityCheck,
)
from aistack.integrity.checks.transport_residue import (
    TransportResidueCheck,
)


def default_checks() -> list[IntegrityCheck]:

    return [
        StructuralIntegrityCheck(),
        MetadataCompletenessCheck(),
        ProjectionFidelityCheck(),
        KnowledgeStateCheck(),
        ClassificationDeclarationCheck(),
        ClassificationCoherenceCheck(),
        PrincipleIdentifierCheck(),
        RegisterCoherenceCheck(),
        DuplicateTitleCheck(),
        TransportResidueCheck(),
        ContractDebtCheck(),
        ReferenceIntegrityCheck(),
    ]


class DefaultKnowledgeIntegrityEngine:
    """
    Compose integrity checks over a Context Bundle.

    The engine only collects evidence. It ranks nothing,
    remediates nothing, and hides nothing: every finding a
    check returns reaches the report.
    """

    def __init__(
        self,
        checks: list[IntegrityCheck] | None = None,
    ):
        self.checks = (
            checks
            if checks is not None
            else default_checks()
        )

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> KnowledgeIntegrityReport:

        findings = []

        for check in self.checks:
            findings.extend(
                check.evaluate(bundle)
            )

        return KnowledgeIntegrityReport(
            bundle_id=bundle.id,
            source_commit=bundle.source_commit,
            artifact_count=len(bundle.artifacts),
            findings=tuple(findings),
        )
