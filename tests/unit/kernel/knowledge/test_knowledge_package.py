from aistack.kernel.knowledge import KnowledgePackage


def test_knowledge_package_preserves_identifier():

    package = KnowledgePackage(
        identifier="knowledge.test",
    )

    assert package.identifier == "knowledge.test"
