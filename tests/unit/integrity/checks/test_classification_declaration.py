from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.classification_declaration import (
    ClassificationDeclarationCheck,
)


def _findings(bundle):
    return ClassificationDeclarationCheck().evaluate(bundle)


def test_a_fully_qualified_heritage_yields_nothing(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(
            source="a.md",
            domain="Foundation",
            semantic_type="Principle",
            criticality="C3",
        ),
    ])

    assert _findings(bundle) == []


def test_undeclared_qualifications_are_warned(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(
            source="a.md",
            domain="unknown",
            semantic_type="unknown",
            criticality="C3",
        ),
    ])

    summaries = {f.summary for f in _findings(bundle)}

    assert "artifacts declare no domain" in summaries
    assert "artifacts declare no semantic type" in summaries
    assert all(
        f.severity is IntegritySeverity.WARNING
        for f in _findings(bundle)
    )


def test_no_core_artifact_is_blocking(make_artifact, make_bundle):
    """
    The blocking condition is the absence of a C3, not the
    uniformity of the values: without a core level there is no
    minimal governed context to acquire.
    """

    bundle = make_bundle([
        make_artifact(source="a.md", criticality="C1"),
        make_artifact(source="b.md", criticality="C2"),
    ])

    blocking = [
        f for f in _findings(bundle)
        if f.severity is IntegritySeverity.BLOCKING
    ]

    assert len(blocking) == 1
    assert "C3" in blocking[0].summary


def test_one_core_artifact_clears_the_blocking(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(source="a.md", criticality="C3"),
        make_artifact(source="b.md", criticality="unknown"),
    ])

    blocking = [
        f for f in _findings(bundle)
        if f.severity is IntegritySeverity.BLOCKING
    ]

    assert blocking == []


def test_undeclared_criticality_is_warned(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(source="a.md", criticality="C3"),
        make_artifact(source="b.md", criticality="unknown"),
    ])

    assert any(
        f.summary == "artifacts declare no criticality"
        and f.affected == 1
        for f in _findings(bundle)
    )


def test_empty_bundle_yields_nothing(make_bundle):

    assert _findings(make_bundle([])) == []
