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
        criticality=1,
        status="Published",
        confidence="high",
        owner="Foundation",
    ):
        now = datetime(2026, 1, 1)

        return KnowledgeArtifact(
            id=source,
            title=title,
            domain="Knowledge Assets",
            semantic_type="Knowledge Artifact",
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
