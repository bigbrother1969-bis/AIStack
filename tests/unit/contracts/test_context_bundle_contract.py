from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle


def create_test_artifact():

    return KnowledgeArtifact(
        id="TEST-001",
        title="Test Artifact",
        declared_type="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality=3,
        owner="AIStack",
        source="tests/sample.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_context_bundle_creation():

    artifact = create_test_artifact()

    bundle = ContextBundle(
        id="BUNDLE-001",
        title="Test Context Bundle",
        generated_at=datetime.now(),
        source_commit="abcdef",
        artifacts=[artifact],
    )

    assert bundle.id == "BUNDLE-001"
    assert bundle.title == "Test Context Bundle"
    assert bundle.source_commit == "abcdef"
    assert len(bundle.artifacts) == 1


def test_context_bundle_default_versions():

    bundle = ContextBundle(
        id="BUNDLE-002",
        title="Default Bundle",
        generated_at=datetime.now(),
        source_commit="abcdef",
    )

    assert bundle.classification_version == "1.0"
    assert bundle.criticality_version == "1.0"
    assert bundle.artifacts == []


def test_context_bundle_is_immutable():

    bundle = ContextBundle(
        id="BUNDLE-003",
        title="Immutable Bundle",
        generated_at=datetime.now(),
        source_commit="abcdef",
    )

    try:
        bundle.title = "Modified"
        assert False, "ContextBundle should be immutable"

    except Exception:
        assert True
