from __future__ import annotations

from typing import Protocol


class AIEngine(Protocol):
    """
    What the AI Runtime asks of any engine that answers its prompts.

    `ARCH-0003-AI-Runtime-Architecture.md`: "The Kernel shall not
    depend on Ollama" — this is the governed contract that keeps
    that true. `aistack.ai_runtime.operations.reason`/`explain`/
    `recommend` (`aistack.ai_runtime.ollama_engine.OllamaEngine`,
    the only implementation today) call this and nothing more
    specific, so a second engine (a different local model server, or
    a cloud one, should the owner ever choose one) is a second class
    satisfying this same shape, not a change to the three operations
    that call it.

    **One method, deliberately.** `reason`/`explain`/`recommend` are
    three different *prompts*, not three different engine
    capabilities — every real model behind an HTTP completion
    endpoint answers a prompt with text, so a single `complete` is
    the whole surface an engine needs to expose. Widening this
    happens when a real engine needs something this shape cannot
    express, not in anticipation of one.

    **Tolerant by contract, the same convention every network
    provider in this heritage already holds** (`BeszelProvider`,
    `NetworkDockerDiscoveryProvider`): a wrong host, a model not
    pulled, an engine that is down are ordinary operating states, not
    exceptions an implementation is allowed to raise. `complete`
    returns the answer and an empty reason on success, or an empty
    answer and a reason on failure — never both non-empty, never
    both empty.
    """

    def complete(self, prompt: str) -> tuple[str, str]:
        """
        Ask the engine to complete `prompt`.

        Returns `(text, "")` on success, or `("", reason)` when the
        engine could not be asked or did not answer.
        """
        ...
