from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.structural_integrity import (
    StructuralIntegrityCheck,
)


def test_conflict_marker_is_blocking(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(content="---\nid: x\n<<<<<<< HEAD\n\n# Body\n"),
    ])

    findings = StructuralIntegrityCheck().evaluate(bundle)

    severities = {f.severity for f in findings}

    assert IntegritySeverity.BLOCKING in severities


def test_unterminated_frontmatter_is_blocking(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(content="---\nartifact:\n  id: x\n\n# Body\n"),
    ])

    findings = StructuralIntegrityCheck().evaluate(bundle)

    assert any(
        "never close" in f.summary
        and f.severity is IntegritySeverity.BLOCKING
        for f in findings
    )


def test_unbalanced_fence_is_warned(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(content="# Body\n\n```text\nopened only\n"),
    ])

    findings = StructuralIntegrityCheck().evaluate(bundle)

    assert any(
        "code fence" in f.summary
        and f.severity is IntegritySeverity.WARNING
        for f in findings
    )


def test_sound_artifact_yields_nothing(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(content="---\nartifact:\n  id: x\n---\n\n# Body\n"),
    ])

    assert StructuralIntegrityCheck().evaluate(bundle) == []
