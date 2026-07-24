from enum import Enum


class KnowledgeDomain(str, Enum):
    FOUNDATION = "Foundation"
    ARCHITECTURE = "Architecture"
    GOVERNANCE = "Governance"
    STANDARDS = "Standards"
    ENGINEERING = "Engineering"
    KNOWLEDGE_ASSETS = "Knowledge Assets"


class SemanticType(str, Enum):
    PRINCIPLE = "Principle"
    RULE = "Rule"
    POLICY = "Policy"
    ADR = "ADR"
    STANDARD = "Standard"
    SPECIFICATION = "Specification"
    KNOWLEDGE_ARTIFACT = "Knowledge Artifact"
