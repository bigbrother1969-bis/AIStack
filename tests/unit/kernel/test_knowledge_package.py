from dataclasses import FrozenInstanceError, is_dataclass

import pytest

from aistack.kernel.models import KnowledgePackage


def test_knowledge_package_requires_an_identifier() -> None:
    with pytest.raises(TypeError):
        KnowledgePackage()


def test_knowledge_package_preserves_its_identifier() -> None:
    package = KnowledgePackage(id="knowledge-package-001")

    assert package.id == "knowledge-package-001"


def test_knowledge_package_is_a_frozen_dataclass() -> None:
    assert is_dataclass(KnowledgePackage)

    package = KnowledgePackage(id="knowledge-package-001")

    with pytest.raises(FrozenInstanceError):
        package.id = "knowledge-package-002"
