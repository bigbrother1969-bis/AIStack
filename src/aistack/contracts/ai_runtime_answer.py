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
    `external` says the question was sent to an engine outside the owner's
    machines, whether or not it answered (`ADR-0029`): the journal records
    it, the answer's text never needs it.
    `route` says what `ai_policy.yml` decided for this call (`internal_only`, or
    `internal_only; not asked: gemini` when an engine was kept out): the journal
    records it, the answer's text never needs it.
    """

    operation: str
    subject: str
    model: str
    prompt: str
    response: str
    reachable: bool
    unreachable_reason: str = ""
    language: str = "fr"
    external: bool = False
    route: str = ""

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
