from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AIRuntimeAnswer:
    """
    One AI Runtime call: the prompt sent and the response received.

    The prompt always travels with the response, so a reader can check
    what produced the answer. This is not a `RuntimeFinding` and is never
    cited as evidence: it is what a language model said, not what a
    deterministic rule observed.

    `reachable`/`unreachable_reason` mirror `AIEngine.complete`: an
    unreachable engine is a reportable outcome, not an exception.
    `language` is the language requested; if no translator ran or the
    translation failed, `response` is still in the model's own language.
    """

    operation: str
    subject: str
    model: str
    prompt: str
    response: str
    reachable: bool
    unreachable_reason: str = ""
    language: str = "fr"

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError("an AI Runtime answer names its own operation")

        if not self.subject.strip():
            raise ValueError("an AI Runtime answer names its own subject")

        if self.reachable and not self.response:
            raise ValueError(
                f"{self.operation} on {self.subject!r} claims reachable "
                f"but carries no response"
            )

        if not self.reachable and not self.unreachable_reason:
            raise ValueError(
                f"{self.operation} on {self.subject!r} claims unreachable "
                f"but names no reason"
            )
