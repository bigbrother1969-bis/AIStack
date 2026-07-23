from __future__ import annotations

from datetime import datetime

from aistack.kernel.knowledge import (
    KnowledgeArtifact,
    KnowledgeLifecycle,
    KnowledgeProvenance,
    KnowledgeScore,
)

from aistack.kernel.services.knowledge import (
    InMemoryKnowledgeArtifactRepository,
)


def create_artifact() -> KnowledgeArtifact:
    return KnowledgeArtifact(
        identifier="artifact.test",
        artifact_type="test",
        name="Test Artifact",
        provenance=KnowledgeProvenance(
            source="unit-test",
            provider="pytest",
        ),
        owner="AIStack",
        created_at=datetime(
            2026,
            7,
            23,
        ),
        version=1,
        score=KnowledgeScore(
            confidence=0.95,
        ),
        lifecycle=KnowledgeLifecycle.DISCOVERED,
        content={
            "value": True,
        },
    )


def test_knowledge_repository_stores_artifact() -> None:

    repository = InMemoryKnowledgeArtifactRepository()

    artifact = create_artifact()

    repository.save(
        artifact,
    )

    stored = repository.get(
        "artifact.test",
    )

    assert stored is artifact


def test_knowledge_repository_lists_artifacts() -> None:

    repository = InMemoryKnowledgeArtifactRepository()

    artifact = create_artifact()

    repository.save(
        artifact,
    )

    artifacts = repository.list()

    assert artifacts == (
        artifact,
    )
