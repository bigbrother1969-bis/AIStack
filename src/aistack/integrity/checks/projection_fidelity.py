from aistack.contracts.classification import (
    normalize_domain,
    normalize_semantic_type,
)
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.criticality import normalize_criticality
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)
from aistack.contracts.undeclared import UNDECLARED

from aistack.context_bundle.builders.frontmatter import (
    parse_artifact_frontmatter,
)


def _verbatim(value) -> str:
    """A field with no vocabulary travels unchanged."""

    if value is None:
        return UNDECLARED

    return str(value).strip() or UNDECLARED


# frontmatter key -> (artifact attribute, expected transform)
CARRIED = (
    ("type", "declared_type", _verbatim),
    ("domain", "domain", normalize_domain),
    ("semantic_type", "semantic_type", normalize_semantic_type),
    ("criticality", "criticality", normalize_criticality),
    ("owner", "owner", _verbatim),
    ("status", "status", _verbatim),
    ("confidence", "confidence", _verbatim),
)


class ProjectionFidelityCheck(IntegrityCheck):
    """
    A projection shall carry what the artifact declared.

    This check compares the frontmatter an artifact wrote with
    the fields the bundle actually carries, and reports every
    value that was declared and did not survive the trip.

    It exists because that defect occurred three times in this
    repository, each time silently, each time discovered only by
    reading the code:

    - the builder hardcoded `criticality=1`, overwriting the C3
      that `ENG-TEST-0001` and `ENG-TEST-0002` had declared;
    - the builder hardcoded `domain` and `owner` likewise;
    - the builder read `type` and stored it *as* `semantic_type`,
      so the `semantic_type: Principle` those same two artifacts
      declared never reached a consumer at all.

    In each case the heritage was correct and the pipeline was
    destroying it in transit. Nothing measured that. A validator
    that only counts what is missing cannot tell the difference
    between knowledge never written and knowledge thrown away —
    and the second is far worse, because the owner has already
    done the work.

    The severity is BLOCKING. A bundle that loses declarations
    is not a projection of the heritage; it is a different
    heritage, and every downstream count computed from it is
    wrong.

    A declared value that no governed vocabulary contains is
    *not* reported here. Normalizing it away is correct
    behaviour, and `classification-declaration` reports it as an
    invalid declaration.
    """

    @property
    def name(self) -> str:
        return "projection-fidelity"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        if not total:
            return []

        lost: dict[str, list[str]] = {}

        for artifact in bundle.artifacts:

            declared = parse_artifact_frontmatter(
                artifact.content
            )

            if not declared:
                continue

            for key, attribute, transform in CARRIED:

                if key not in declared:
                    continue

                expected = transform(declared[key])

                if expected == UNDECLARED:
                    # Either empty, or outside its vocabulary.
                    # Dropping it is correct; another check
                    # reports the invalid declaration.
                    continue

                if getattr(artifact, attribute) != expected:
                    lost.setdefault(key, []).append(
                        artifact.source
                    )

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.BLOCKING,
                summary=(
                    f"artifacts declare {key} but the "
                    "projection does not carry it; the "
                    "pipeline is destroying knowledge in "
                    "transit"
                ),
                affected=len(subjects),
                total=total,
                subjects=tuple(subjects),
            )
            for key, subjects in lost.items()
        ]
