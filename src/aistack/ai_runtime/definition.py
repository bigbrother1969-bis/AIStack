from __future__ import annotations

from dataclasses import dataclass

from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class AIRuntimeDefinition:
    """
    Where the AI Runtime's first engine is reached — J6,
    `claude/PLAN-TRAJECTOIRE-2026-09-04.md` ("AI Runtime:
    reason/explain/recommend"), and `ARCH-0003-AI-Runtime
    -Architecture.md` / `CMP-0006-README.md` (both `Draft`): "Ollama
    is a possible local AI Engine implementation. The Kernel shall
    not depend on Ollama."

    **`host`/`port` are the owner's own real facts, confirmed
    2026-09-13, not a guess at Ollama's usual default** — an Ollama
    instance already runs on GIGABYTE, port 11434 (Ollama's own
    documented default, but stated here because the owner confirmed
    it against the real instance, not assumed from the port alone).

    **`model` starts `None`, and that is a real, honest state, not a
    placeholder to fill in later "properly."** The owner did not have
    the exact installed model name in hand when this was declared
    (`ollama list` on GIGABYTE names it) — `FDN-0003` Article 12: an
    undetermined fact is declared as absent, never guessed at a
    plausible-sounding default (`llama3.1:8b` and similar names were
    offered as multiple-choice conveniences during scoping, never
    written here as if confirmed). `aistack.cli.ai_reason` reports
    this absence plainly and exits rather than sending Ollama a model
    name nobody confirmed is installed.

    **`timeout` defaults to `OllamaEngine`'s own default
    (`DEFAULT_TIMEOUT_SECONDS`, imported rather than repeated as a
    second `120.0` literal — one number, one place).** Added
    2026-09-25 because the model choice itself became a real
    speed/reliability tradeoff the owner needed to declare, not just
    the model name: `qwen2.5:0.5b` (chosen 2026-09-18, ~15.7s average
    in QUAL-0001) comfortably fits the 120s default, but
    `deepseek-r1:1.5b` (~500s average, up to ~623.5s observed on the
    richest context in that same campaign,
    `claude/QUAL-0001-GOVERNED-LLM-EXPERIMENTS-HANDOVER.md` § 10)
    would almost always exceed it. A declared, generous `timeout`
    lets the owner choose the slower, more reliable model (QUAL-0001
    §13: `deepseek-r1:1.5b` passed the closed YES/NO reliability test
    `qwen2.5:0.5b` failed) without the call being cut off before it
    finishes — the same "chosen as a first, generous number to revise
    once timed for real" discipline `OllamaEngine`'s own default
    states for itself.

    This declares only what this first AI Engine implementation
    needs. `ARC-P-006` — no `engine:` discriminator field is added
    for a second, hypothetical engine type; `OllamaEngine` is the only
    implementation `aistack.ai_runtime.engine.AIEngine` has today, and
    widening this shape happens when a second real engine exists to
    justify it, not before.
    """

    host: str
    port: int
    model: str | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
