from dataclasses import is_dataclass

from aistack.kernel.models import KnowledgePackage


def test_knowledge_package_is_a_frozen_dataclass() -> None:
    assert is_dataclass(KnowledgePackage)

    package = KnowledgePackage()

    assert isinstance(package, KnowledgePackage)
