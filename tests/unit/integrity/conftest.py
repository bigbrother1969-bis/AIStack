from datetime import datetime

import pytest

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle


@pytest.fixture
def make_artifact():

    def _make(
        source="docs/a.md",
        title="a",
        content="# a\n",
        criticality="C1",
        status="Published",
        confidence="high",
        owner="Foundation",
        domain="Foundation",
        semantic_type="Principle",
    ):
        now = datetime(2026, 1, 1)

        return KnowledgeArtifact(
            id=source,
            title=title,
            declared_type="Test Artifact",
            domain=domain,
            semantic_type=semantic_type,
            criticality=criticality,
            owner=owner,
            source=source,
            content=content,
            status=status,
            confidence=confidence,
            created_at=now,
            updated_at=now,
        )

    return _make


@pytest.fixture
def make_bundle():

    def _make(artifacts):
        return ContextBundle(
            id="bundle-test",
            title="Test Bundle",
            generated_at=datetime(2026, 1, 1),
            source_commit="abc1234",
            artifacts=list(artifacts),
        )

    return _make
