from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.knowledge_registry import (
    KnowledgeRegistry,
)
from aistack.context_bundle.generation.context_bundle_builder import (
    DefaultContextBundleBuilder,
)


def test_context_bundle_builder_creates_bundle():

    artifact = KnowledgeArtifact(
        id="TEST-001",
        title="Test Artifact",
        declared_type="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality=3,
        owner="AIStack",
        source="test.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    registry = KnowledgeRegistry()

    registry.add(artifact)

    builder = DefaultContextBundleBuilder()

    bundle = builder.build(
        registry,
        source_commit="abcdef",
    )

    assert bundle.source_commit == "abcdef"
    assert bundle.title == "AIStack Context Bundle"
    assert len(bundle.artifacts) == 1
    assert bundle.artifacts[0].id == "TEST-001"


# --------------------------------------------------------------------
# The contract architecture the projection carries
# --------------------------------------------------------------------


def _registry() -> KnowledgeRegistry:

    registry = KnowledgeRegistry()

    registry.add(
        KnowledgeArtifact(
            id="TEST-002",
            title="Another",
            declared_type="Test Artifact",
            domain="Foundation",
            semantic_type="Principle",
            criticality=3,
            owner="AIStack",
            source="other.md",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )

    return registry


def test_the_builder_carries_the_measurement_it_is_given():
    """
    The measurement is injected rather than called directly, so
    that a caller with no source tree to walk is not forced to
    pretend it has one — and so the suite does not import 298
    modules on every test that builds a bundle.

    Found by mutation on 2026-08-22: replacing the call with
    `None` left every test green. Nothing checked that a builder
    given a measurement actually used it.
    """

    from aistack.contracts.contract_inventory import ContractInventory

    measured = ContractInventory(
        package="aistack", modules=3, implementations=1
    )

    bundle = DefaultContextBundleBuilder(
        measure_contracts=lambda: measured,
    ).build(_registry(), "abc1234")

    assert bundle.contract_inventory is measured


def test_a_builder_given_nothing_carries_nothing():
    """
    `None` is a governed state under FDN-0003 Article 12, and the
    integrity check reads it as *undeclared*, never as zero
    orphan contracts.
    """

    bundle = DefaultContextBundleBuilder().build(
        _registry(), "abc1234"
    )

    assert bundle.contract_inventory is None
