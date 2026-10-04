"""
The AI half of a guided diagnosis (`ADR-0012` § 4): `reason`,
`explain` and `recommend` over one real finding, in the reader's
language — the three calls `aistack.cli.ai_reason` makes.

**One operation at a time, in the background (2026-10-03).** With
`deepseek-r1:1.5b` on GIGABYTE's CPU a single call takes several
minutes (`QUAL-0001`), so the screen no longer holds a request open
for all three: `/start` hands `run_diagnosis` to a background worker
and the steps show each answer as soon as it exists. The three answers
are still recorded together, as one AI Reasoning History entry, once
the last one arrives (J7 decision #2).

**The declared `timeout` reaches the engine.** The screen built its
engines without it from the day `ai_runtime.yml` declared
`timeout: 900` — the CLI passed it, the screen fell back to the
engine's 120 s and reported a slow model as an unreachable one.
"""

from __future__ import annotations

from aistack.config import configured

import re
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Any

from aistack.ai_runtime.ollama_engine import OllamaEngine
from aistack.ai_runtime.operations import explain, reason, recommend
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding

AI_RUNTIME = configured(Path(__file__).resolve().parents[1] / "ai_runtime" / "definitions" / "ai_runtime.yml")

OPERATIONS = ("reason", "explain", "recommend")
STEP_COUNT = 4
OPERATION_BY_STEP: dict[int, str] = {2: "reason", 3: "explain", 4: "recommend"}

# (finding, operation, target language) -> one answer.
AskAI = Callable[[RuntimeFinding, str, str], AIRuntimeAnswer]
Record = Callable[[RuntimeFinding, tuple[AIRuntimeAnswer, ...]], Any]

_CALLS = {"reason": reason, "explain": explain, "recommend": recommend}


def ask_ollama(finding: RuntimeFinding, operation: str, target_language: str) -> AIRuntimeAnswer:
    """
    One answer from the model `ai_runtime.yml` declares, within its
    declared `timeout`. A second, fast model translates into
    `target_language` whenever it is not English, and only when
    `translator_model:` is declared (`aistack.ai_runtime.operations`).
    """

    definition = load_ai_runtime_yaml(AI_RUNTIME)
    engine = OllamaEngine(
        host=definition.host,
        port=definition.port,
        model=definition.model or "",
        timeout=definition.timeout,
    )
    translator = (
        OllamaEngine(
            host=definition.host,
            port=definition.port,
            model=definition.translator_model,
            timeout=definition.timeout,
        )
        if definition.translator_model
        else None
    )

    return _CALLS[operation](
        finding,
        engine,
        definition.model,
        target_language=target_language,
        translator=translator,
    )


def run_diagnosis(
    finding: RuntimeFinding,
    target_language: str,
    answers: MutableMapping[str, AIRuntimeAnswer],
    ask: AskAI,
    record: Record,
) -> None:
    """
    Ask the three operations in order, storing each answer in `answers`
    the moment it arrives, then record the three together.
    """

    for operation in OPERATIONS:
        answers[operation] = ask(finding, operation, target_language)

    record(finding, tuple(answers[operation] for operation in OPERATIONS))


# What `OllamaEngine` and `aistack.ai_runtime.operations` say when no
# answer came back, read into a catalog key and its parameters so the
# screen says it in the reader's language. Anything not recognised is
# shown as the engine wrote it, never guessed into a category.
_TIMEOUT = re.compile(r"did not answer within (?P<seconds>[\d.]+) seconds")
_REFUSED = re.compile(r"refused the request with status (?P<status>\d+)")
_UNREACHABLE = re.compile(r"could not be reached: (?P<detail>.*)")


def describe_unreachable(reason_text: str) -> tuple[str, dict[str, str]]:
    """The catalog key and parameters for why the AI engine gave no answer."""

    if match := _TIMEOUT.search(reason_text):
        seconds = float(match["seconds"])
        return "troubleshooting.unreachable.timeout", {"seconds": f"{seconds:g}"}

    if match := _REFUSED.search(reason_text):
        return "troubleshooting.unreachable.refused", {"status": match["status"]}

    if match := _UNREACHABLE.search(reason_text):
        return "troubleshooting.unreachable.unreachable", {"detail": match["detail"]}

    if reason_text.startswith("no model is configured"):
        return "troubleshooting.unreachable.no_model", {}

    return "troubleshooting.unreachable.other", {"detail": reason_text}
