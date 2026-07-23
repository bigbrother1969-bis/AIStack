from aistack.kernel.knowledge import (
    KnowledgeArtifact,
    KnowledgeLifecycle,
    KnowledgeProvenance,
    KnowledgeScore,
)


def test_knowledge_artifact_preserves_governance_metadata() -> None:

    artifact = KnowledgeArtifact(
        identifier="artifact.test",
        artifact_type="test",
        name="Test Artifact",
        provenance=KnowledgeProvenance(
            source="unit-test",
            provider="pytest",
        ),
        owner="AIStack",
        score=KnowledgeScore(
            confidence=0.95,
        ),
        lifecycle=KnowledgeLifecycle.DISCOVERED,
        content={
            "value": True,
        },
    )

    assert artifact.identifier == "artifact.test"
    assert artifact.provenance.source == "unit-test"
    assert artifact.owner == "AIStack"
    assert artifact.score.confidence == 0.95
    assert artifact.lifecycle is KnowledgeLifecycle.DISCOVERED
