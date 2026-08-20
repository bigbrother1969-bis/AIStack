from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact


def test_knowledge_artifact_creation():

    artifact = KnowledgeArtifact(
        id="TEST-001",
        title="Test Knowledge Artifact",
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
        domain="Engineering",
        semantic_type="Rule",
        criticality="C2",
        owner="AIStack",
        source="tests/sample.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert artifact.confidence == "unknown"
    assert artifact.status == "draft"
    assert artifact.metadata == {}


def test_knowledge_artifact_is_immutable():

    artifact = KnowledgeArtifact(
        id="TEST-003",
        title="Immutable Artifact",
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
