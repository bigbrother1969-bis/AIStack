from __future__ import annotations

import pytest

from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer


def test_a_reachable_answer_carries_a_response():
    answer = AIRuntimeAnswer(
        operation="reason",
        subject="booklore_db",
        model="llama3.1:8b",
        prompt="...",
        response="a real answer",
        reachable=True,
    )

    assert answer.response == "a real answer"


def test_reachable_with_no_response_is_rejected():
    with pytest.raises(ValueError, match="no response"):
        AIRuntimeAnswer(
            operation="reason",
            subject="booklore_db",
            model="llama3.1:8b",
            prompt="...",
            response="",
            reachable=True,
        )


def test_unreachable_with_no_reason_is_rejected():
    with pytest.raises(ValueError, match="names no reason"):
        AIRuntimeAnswer(
            operation="reason",
            subject="booklore_db",
            model="llama3.1:8b",
            prompt="...",
            response="",
            reachable=False,
            unreachable_reason="",
        )


def test_an_unreachable_answer_carries_its_reason():
    answer = AIRuntimeAnswer(
        operation="reason",
        subject="booklore_db",
        model="",
        prompt="",
        response="",
        reachable=False,
        unreachable_reason="no model is configured",
    )

    assert answer.unreachable_reason == "no model is configured"


def test_an_empty_operation_is_rejected():
    with pytest.raises(ValueError, match="operation"):
        AIRuntimeAnswer(
            operation="",
            subject="booklore_db",
            model="llama3.1:8b",
            prompt="...",
            response="an answer",
            reachable=True,
        )


def test_an_empty_subject_is_rejected():
    with pytest.raises(ValueError, match="subject"):
        AIRuntimeAnswer(
            operation="reason",
            subject="",
            model="llama3.1:8b",
            prompt="...",
            response="an answer",
            reachable=True,
        )
