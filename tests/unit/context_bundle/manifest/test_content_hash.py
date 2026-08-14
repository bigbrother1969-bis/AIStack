from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact

from aistack.context_bundle.manifest.content_hash import (
    compute_content_hash,
)


def _artifact(identifier: str) -> KnowledgeArtifact:

    return KnowledgeArtifact(
        id=identifier,
        title=identifier,
        domain="Knowledge Assets",
        semantic_type="Knowledge Artifact",
        criticality=1,
        owner="Foundation",
        source=f"/{identifier}.md",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def test_content_hash_is_stable():

    artifacts = [
        _artifact("aaa"),
        _artifact("bbb"),
    ]

    assert (
        compute_content_hash(artifacts)
        == compute_content_hash(artifacts)
    )


def test_content_hash_ignores_ordering():
    """
    Two bundles carrying the same knowledge must share
    the same fingerprint, whatever the discovery order.
    """

    first = [
        _artifact("aaa"),
        _artifact("bbb"),
    ]

    second = [
        _artifact("bbb"),
        _artifact("aaa"),
    ]

    assert (
        compute_content_hash(first)
        == compute_content_hash(second)
    )


def test_content_hash_detects_change():

    before = [_artifact("aaa")]

    after = [
        _artifact("aaa"),
        _artifact("bbb"),
    ]

    assert (
        compute_content_hash(before)
        != compute_content_hash(after)
    )


def test_content_hash_of_empty_bundle():

    assert len(compute_content_hash([])) == 64
