from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.criticality_discrimination import (
    CriticalityDiscriminationCheck,
)


def test_uniform_criticality_is_blocking(make_artifact, make_bundle):
    """
    The bootstrap protocol mandates a Criticality Evaluation
    step. With a single level present there is nothing to
    evaluate.
    """

    bundle = make_bundle([
        make_artifact(source="a.md", criticality=1),
        make_artifact(source="b.md", criticality=1),
    ])

    findings = CriticalityDiscriminationCheck().evaluate(bundle)

    assert len(findings) == 1
    assert findings[0].severity is IntegritySeverity.BLOCKING
    assert findings[0].affected == 2


def test_discriminated_criticality_yields_nothing(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(source="a.md", criticality=3),
        make_artifact(source="b.md", criticality=1),
    ])

    assert CriticalityDiscriminationCheck().evaluate(bundle) == []


def test_empty_bundle_yields_nothing(make_bundle):

    assert CriticalityDiscriminationCheck().evaluate(make_bundle([])) == []
