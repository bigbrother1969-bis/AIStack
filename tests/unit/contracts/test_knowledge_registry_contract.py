from datetime import datetime

import pytest

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.knowledge_registry import KnowledgeRegistry


def create_artifact(id="TEST-001"):

    return KnowledgeArtifact(
        id=id,
        title="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality=3,
        owner="AIStack",
        source="test.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_registry_add_artifact():

    registry = KnowledgeRegistry()

    artifact = create_artifact()

    registry.add(artifact)

    assert registry.count() == 1


def test_registry_get_artifact():

    registry = KnowledgeRegistry()

    artifact = create_artifact()

    registry.add(artifact)

    result = registry.get("TEST-001")

    assert result == artifact


def test_registry_reject_duplicate_id():

    registry = KnowledgeRegistry()

    registry.add(create_artifact())

    with pytest.raises(ValueError):

        registry.add(create_artifact())
