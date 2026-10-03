"""`aistack.troubleshooting.guide` — the declared timeout, the order, the engine's silences."""

from __future__ import annotations

from typing import Any

import pytest

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.i18n import translator_for
from aistack.troubleshooting import guide
from aistack.troubleshooting.guide import OPERATIONS, describe_unreachable, run_diagnosis


def test_the_engines_receive_the_declared_timeout(monkeypatch: pytest.MonkeyPatch):
    built: list[dict[str, Any]] = []

    class Recording(OllamaEngine):
        def __init__(self, **kwargs: Any) -> None:
            built.append(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(guide, "OllamaEngine", Recording)
    monkeypatch.setitem(guide._CALLS, "reason", lambda *args, **kwargs: "answered")

    assert guide.ask_ollama(object(), "reason", "fr") == "answered"  # type: ignore[arg-type]

    declared = guide.load_ai_runtime_yaml(guide.AI_RUNTIME).timeout
    assert built and all(kwargs["timeout"] == declared for kwargs in built)


def test_the_answers_arrive_in_order_and_are_recorded_together():
    answers: dict[str, Any] = {}
    seen: list[tuple[str, dict[str, Any]]] = []
    recorded: list[tuple[Any, ...]] = []

    def ask(finding: Any, operation: str, language: str) -> str:
        seen.append((operation, dict(answers)))
        return f"{operation}:{language}"

    run_diagnosis("finding", "fr", answers, ask, lambda f, done: recorded.append(done))  # type: ignore[arg-type]

    assert [operation for operation, _ in seen] == list(OPERATIONS)
    assert seen[1][1] == {"reason": "reason:fr"}
    assert recorded == [("reason:fr", "explain:fr", "recommend:fr")]


@pytest.mark.parametrize(
    ("reason", "key", "parameters"),
    [
        (
            "Ollama at 127.0.0.1:11434 did not answer within 900.0 seconds",
            "troubleshooting.unreachable.timeout",
            {"seconds": "900"},
        ),
        (
            "Ollama refused the request with status 404 (Not Found): model not found",
            "troubleshooting.unreachable.refused",
            {"status": "404"},
        ),
        (
            "Ollama at 127.0.0.1:11434 could not be reached: [Errno 111] Connection refused",
            "troubleshooting.unreachable.unreachable",
            {"detail": "[Errno 111] Connection refused"},
        ),
        (
            "no model is configured (aistack.ai_runtime.definitions.ai_runtime.yml has no model:)",
            "troubleshooting.unreachable.no_model",
            {},
        ),
        ("something new", "troubleshooting.unreachable.other", {"detail": "something new"}),
    ],
)
def test_each_silence_of_the_engine_has_its_message(reason: str, key: str, parameters: dict[str, str]):
    assert describe_unreachable(reason) == (key, parameters)

    for lang in ("fr", "en"):
        assert translator_for(lang)(key, **parameters)
