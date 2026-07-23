from aistack.kernel.knowledge import KnowledgePackage
from aistack.kernel.services.knowledge import (
    InMemoryKnowledgeRepository,
)


def test_knowledge_repository_stores_package():

    repository = InMemoryKnowledgeRepository()

    package = KnowledgePackage(
        identifier="knowledge.test",
    )

    repository.store(package)

    assert repository.get(
        "knowledge.test"
    ) is package
