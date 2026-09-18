from aistack.contracts.knowledge_lifecycle import KnowledgeLifecycle


def test_knowledge_lifecycle_states_exist():

    assert KnowledgeLifecycle.DISCOVERED == "discovered"
    assert KnowledgeLifecycle.VALIDATED == "validated"
    assert KnowledgeLifecycle.ACTIVE == "active"
    assert KnowledgeLifecycle.ARCHIVED == "archived"
