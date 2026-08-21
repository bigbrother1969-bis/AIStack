from dataclasses import MISSING, fields
from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact


def test_knowledge_artifact_creation():

    artifact = KnowledgeArtifact(
        id="TEST-001",
        title="Test Knowledge Artifact",
        declared_type="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality="C3",
        owner="AIStack",
        source="tests/sample.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert artifact.id == "TEST-001"
    assert artifact.title == "Test Knowledge Artifact"
    assert artifact.domain == "Foundation"
    assert artifact.semantic_type == "Principle"
    assert artifact.criticality == "C3"


def test_knowledge_artifact_default_values():

    artifact = KnowledgeArtifact(
        id="TEST-002",
        title="Default Test Artifact",
        declared_type="Test Artifact",
        domain="Engineering",
        semantic_type="Rule",
        criticality="C2",
        owner="AIStack",
        source="tests/sample.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert artifact.confidence == "unknown"
    assert artifact.status == "unknown"
    assert artifact.metadata == {}


def test_no_default_invents_a_qualification():
    """
    `status` defaulted to "draft" until 2026-08-21 — a lifecycle
    state the contract assigned on the human's behalf whenever a
    producer omitted it, which 9 of 15 call sites did.

    FDN-0003 Article 12: an undeclared value is a governed state
    and must stay visible. A default may say "not declared"; it
    may never say something plausible instead.

    The four qualifications carry no default at all, so a
    producer has to state them — even to state that they are
    unknown.
    """

    defaults = {
        f.name: f.default
        for f in fields(KnowledgeArtifact)
        if f.default is not MISSING
    }

    assert defaults["status"] == "unknown"
    assert defaults["confidence"] == "unknown"

    for name in (
        "declared_type",
        "domain",
        "semantic_type",
        "criticality",
    ):
        assert name not in defaults, (
            f"{name} is a qualification: a producer must state "
            "it, even to state that it is unknown"
        )


def test_knowledge_artifact_is_immutable():

    artifact = KnowledgeArtifact(
        id="TEST-003",
        title="Immutable Artifact",
        declared_type="Test Artifact",
        domain="Architecture",
        semantic_type="ADR",
        criticality="C3",
        owner="AIStack",
        source="tests/sample.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    try:
        artifact.title = "Modified"
        assert False, "KnowledgeArtifact should be immutable"

    except Exception:
        assert True
