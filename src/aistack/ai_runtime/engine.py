from __future__ import annotations

from typing import Protocol


class AIEngine(Protocol):
    """
    What the AI Runtime asks of any engine that answers its prompts.

    The operations in `aistack.ai_runtime.operations` depend only on this
    shape, so the kernel never depends on a specific engine. One method:
    the operations differ by prompt, not by engine capability.

    Tolerant by contract: an unreachable engine, a model not pulled or a
    timeout are reported, never raised. `complete` returns either
    `(text, "")` or `("", reason)`, never both non-empty, never both empty.
    """

    def complete(self, prompt: str) -> tuple[str, str]:
        """
        Ask the engine to complete `prompt`.

        Returns `(text, "")` on success, or `("", reason)` when the
        engine could not be asked or did not answer.
        """
        ...
