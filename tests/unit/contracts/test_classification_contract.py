from aistack.contracts.classification import (
    KnowledgeDomain,
    SemanticType,
)


def test_all_knowledge_domains_exist():

    assert KnowledgeDomain.FOUNDATION.value == "Foundation"
    assert KnowledgeDomain.ARCHITECTURE.value == "Architecture"
    assert KnowledgeDomain.GOVERNANCE.value == "Governance"
    assert KnowledgeDomain.STANDARDS.value == "Standards"
    assert KnowledgeDomain.ENGINEERING.value == "Engineering"
    assert KnowledgeDomain.OPERATIONS.value == "Operations"
    assert KnowledgeDomain.KNOWLEDGE_ASSETS.value == "Knowledge Assets"


def test_all_semantic_types_exist():

    assert SemanticType.PRINCIPLE.value == "Principle"
    assert SemanticType.RULE.value == "Rule"
    assert SemanticType.POLICY.value == "Policy"
    assert SemanticType.ADR.value == "ADR"
    assert SemanticType.STANDARD.value == "Standard"
    assert SemanticType.SPECIFICATION.value == "Specification"
    assert SemanticType.KNOWLEDGE_ARTIFACT.value == "Knowledge Artifact"
