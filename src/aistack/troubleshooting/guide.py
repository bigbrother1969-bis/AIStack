"""
The AI half of a guided diagnosis (`ADR-0012` § 4): `reason`,
`explain` and `recommend` over one real finding, in the reader's
language — exactly the three calls `aistack.cli.ai_reason` makes — and
their recording as one AI Reasoning History entry before a single step
is shown: traceability does not wait on whether the owner clicks
through the wizard (J7 decision #2).

The route receives `ask_ai` as a collaborator, so a test replaces
Ollama; it is the only host-touching call the guide makes.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding

AI_RUNTIME = Path(__file__).resolve().parents[1] / "ai_runtime" / "definitions" / "ai_runtime.yml"

Answers = tuple[AIRuntimeAnswer, AIRuntimeAnswer, AIRuntimeAnswer]
AskAI = Callable[[RuntimeFinding, str], Answers]

STEP_COUNT = 4
OPERATION_BY_STEP: dict[int, str] = {2: "reason", 3: "explain", 4: "recommend"}


def ask_ollama(finding: RuntimeFinding, target_language: str) -> Answers:
    """
    The three answers, from the model `ai_runtime.yml` declares.

    The engine is built even when `model` is empty — the same note
    `aistack.cli.ai_reason.main()` carries. A second, fast model
    translates into `target_language` whenever it is not English, and
    only when `translator_model:` is declared: otherwise every answer
    travels exactly as the model gave it (`aistack.ai_runtime
    .operations`).
    """

    definition = load_ai_runtime_yaml(AI_RUNTIME)
    engine = OllamaEngine(host=definition.host, port=definition.port, model=definition.model or "")
    translator = (
        OllamaEngine(host=definition.host, port=definition.port, model=definition.translator_model)
        if definition.translator_model
        else None
    )

    return (
        reason(finding, engine, definition.model, target_language=target_language, translator=translator),
        explain(finding, engine, definition.model, target_language=target_language, translator=translator),
        recommend(finding, engine, definition.model, target_language=target_language, translator=translator),
    )
