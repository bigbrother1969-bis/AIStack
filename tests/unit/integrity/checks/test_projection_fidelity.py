from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.projection_fidelity import (
    ProjectionFidelityCheck,
)


DECLARED = """---
artifact:
  id: ENG-TEST-0001
  title: Mandatory Unit Testing Principle
  type: Foundation Principle
  semantic_type: Principle
  domain: Engineering
  criticality: C3
  owner: Engineering
  status: Draft
---

# Body
"""


def _findings(bundle):
    return ProjectionFidelityCheck().evaluate(bundle)


def test_a_faithful_projection_yields_nothing(
    make_artifact,
    make_bundle,
):

    bundle = make_bundle(
        [
            make_artifact(
                content=DECLARED,
                title="Mandatory Unit Testing Principle",
                criticality="C3",
                domain="Engineering",
                semantic_type="Principle",
                owner="Engineering",
                status="Draft",
            )
        ]
    )

    findings = [
        f for f in _findings(bundle) if f.subjects
    ]

    # `type` is the one field the shared fixture cannot carry,
    # since it hardcodes declared_type for every artifact.
    assert all(
        "declare type" in f.summary for f in findings
    )


def test_a_destroyed_declaration_is_blocking(
    make_artifact,
    make_bundle,
):
    """
    The regression this check exists for: the artifact declared
    C3, the projection carries C1.

    That is what `MarkdownArtifactBuilder` did until 2026-08-20
    with a hardcoded `criticality=1`, and no check saw it.
    """

    bundle = make_bundle(
        [make_artifact(content=DECLARED, criticality="C1")]
    )

    lost = [
        f
        for f in _findings(bundle)
        if "criticality" in f.summary
    ]

    assert len(lost) == 1
    assert lost[0].severity is IntegritySeverity.BLOCKING
    assert lost[0].affected == 1


def test_a_semantic_type_stored_as_something_else_is_blocking(
    make_artifact,
    make_bundle,
):
    """
    The second regression: the builder read `type` and stored it
    *as* `semantic_type`, so "Principle" never reached a
    consumer while "Foundation Principle" impersonated a
    governed vocabulary term.
    """

    bundle = make_bundle(
        [
            make_artifact(
                content=DECLARED,
                semantic_type="Foundation Principle",
            )
        ]
    )

    lost = [
        f
        for f in _findings(bundle)
        if "semantic_type" in f.summary
    ]

    assert len(lost) == 1
    assert lost[0].severity is IntegritySeverity.BLOCKING


def test_an_invalid_declaration_is_not_a_fidelity_problem(
    make_artifact,
    make_bundle,
):
    """
    An out-of-vocabulary value is *correctly* dropped. Reporting
    it here would blame the pipeline for obeying the standard —
    `classification-declaration` reports it as an invalid
    declaration instead.
    """

    content = DECLARED.replace(
        "  domain: Engineering\n",
        "  domain: Infrastructure\n",
    )

    bundle = make_bundle(
        [make_artifact(content=content, domain="unknown")]
    )

    assert not [
        f for f in _findings(bundle) if "domain" in f.summary
    ]


def test_an_artifact_without_frontmatter_is_not_a_fidelity_problem(
    make_artifact,
    make_bundle,
):

    bundle = make_bundle(
        [make_artifact(content="# No frontmatter\n")]
    )

    assert _findings(bundle) == []
