from dataclasses import FrozenInstanceError

import pytest

from aistack.contracts.knowledge_score import KnowledgeScore


def test_knowledge_score_carries_a_confidence():

    score = KnowledgeScore(confidence=0.95)

    assert score.confidence == 0.95


def test_knowledge_score_is_immutable():

    score = KnowledgeScore(confidence=0.95)

    with pytest.raises(FrozenInstanceError):
        score.confidence = 0.5
