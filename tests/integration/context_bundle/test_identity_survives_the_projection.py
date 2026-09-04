from datetime import datetime
from pathlib import Path

from aistack.context_bundle.export.zip_bundle_exporter import (
    ZipBundleExporter,
)
from aistack.context_bundle.manifest.content_hash import (
    compute_content_hash,
)
from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.integrity.bundle_reader import read_bundle


NOW = datetime(2026, 8, 23, 12, 0, 0)


def artifact(identifier: str, digest: str) -> KnowledgeArtifact:
    return KnowledgeArtifact(
        id=identifier,
        title=f"Title of {identifier}",
        declared_type="t",
        domain="Foundation",
        semantic_type="Principle",
        criticality="C3",
        owner="Foundation",
        source=f"docs/{identifier}.md",
        content=f"---\nartifact:\n  id: {identifier}\n---\n\n# Body\n",
        metadata={"content_hash": digest},
        created_at=NOW,
        updated_at=NOW,
    )


def bundle() -> ContextBundle:
    return ContextBundle(
        id="test-bundle",
        title="Test",
        generated_at=NOW,
        source_commit="abc1234",
        repository_url="https://forge.example.org/aistack.git",
        artifacts=[
            artifact("FDN-0003", "a" * 64),
            artifact("STD-0100", "b" * 64),
        ],
    )


def exported(tmp_path: Path) -> ContextBundle:
    """
    Written and read back the way a mirror consumer would.

    STD-0002: the archive goes to `tmp_path`, never over the
    repository's published projection.
    """

    path = tmp_path / "bundle.zip"

    ZipBundleExporter().export(bundle(), path)

    return read_bundle(path)


def test_the_governed_identifier_survives_the_projection(tmp_path):
    """
    Since 2026-08-23 `id` is what the artifact declares, so a
    consumer holding only the archive can resolve `FDN-0003`.
    Before that it was a content hash and this was impossible
    without parsing 65 frontmatter blocks (GOV-0002/OS-021).
    """

    restored = exported(tmp_path)

    assert {a.id for a in restored.artifacts} == {"FDN-0003", "STD-0100"}


def test_the_repository_url_survives_the_projection(tmp_path):
    """
    `JsonBundleExporter` never writes `repository_url` into
    `bundle.json` — only `ZipBundleExporter`'s `manifest.json`
    carries it. `read_bundle` used to construct `ContextBundle`
    without a `repository_url` argument at all, so this always
    came back as the dataclass default, `"unknown"`, even for a
    bundle that declared a real one (GOV-0002/OS-053).
    """

    restored = exported(tmp_path)

    assert restored.repository_url == "https://forge.example.org/aistack.git"


def test_the_content_hash_survives_the_projection(tmp_path):
    """
    Found by mutation: nothing checked that the hash reached the
    archive or came back from it. Both could be removed with the
    whole suite green.
    """

    restored = exported(tmp_path)

    digests = {
        a.id: a.metadata.get("content_hash") for a in restored.artifacts
    }

    assert digests == {"FDN-0003": "a" * 64, "STD-0100": "b" * 64}


def test_the_fingerprint_is_the_same_before_and_after_the_round_trip(
    tmp_path,
):
    """
    The property the whole thing exists for: a bundle obtained
    from a mirror must be provably equivalent to the one produced
    from the SPOT. A consumer recomputes the fingerprint from what
    it received and compares it to the manifest.

    That only holds while the content hash survives the round
    trip. If it were dropped, `compute_content_hash` would fall
    back to the identifiers and quietly fingerprint the *names* —
    two bundles carrying the same 65 names over different text
    would then prove equivalent.
    """

    before = compute_content_hash(bundle().artifacts)

    after = compute_content_hash(exported(tmp_path).artifacts)

    assert after == before


def test_the_fingerprint_changes_when_content_changes(tmp_path):
    """
    The control case, and it is the one that matters. A
    fingerprint derived from identifiers alone would be identical
    here, since both bundles declare the same two artifacts.
    """

    same_names_other_content = [
        artifact("FDN-0003", "c" * 64),
        artifact("STD-0100", "d" * 64),
    ]

    assert compute_content_hash(same_names_other_content) != (
        compute_content_hash(bundle().artifacts)
    )


def test_the_fingerprint_ignores_ordering(tmp_path):
    """
    Stated by `compute_content_hash` and asserted here: two
    projections of the same heritage must agree whatever order
    discovery walked the tree in.
    """

    forward = bundle().artifacts

    assert compute_content_hash(list(reversed(forward))) == (
        compute_content_hash(forward)
    )
