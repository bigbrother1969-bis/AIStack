from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.knowledge_state import (
    KnowledgeStateCheck,
)


def test_declared_state_yields_nothing(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(status="Published", confidence="high"),
    ])

    assert KnowledgeStateCheck().evaluate(bundle) == []


def test_undeclared_status_is_warned(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact(status="unknown")])

    findings = KnowledgeStateCheck().evaluate(bundle)

    assert any(
        "status" in f.summary
        and f.severity is IntegritySeverity.WARNING
        for f in findings
    )


def test_undeclared_confidence_is_observed(make_artifact, make_bundle):
    """
    Article 3 requires confidence, but nothing in the heritage
    declares it yet. The gap is stated, not treated as a
    governed rule already in force.
    """

    bundle = make_bundle([make_artifact(confidence="unknown")])

    findings = KnowledgeStateCheck().evaluate(bundle)

    assert any(
        "confidence" in f.summary
        and f.severity is IntegritySeverity.OBSERVATION
        for f in findings
    )
