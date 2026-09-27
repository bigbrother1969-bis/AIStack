from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AIRuntimeAnswer:
    """
    One AI Runtime call, in full — J6,
    `claude/PLAN-TRAJECTOIRE-2026-09-04.md`.

    **`prompt` travels alongside `response`, always.** `ARCH-0003`'s
    own principle — "AI is a reasoning assistant, never a source of
    truth" — only means something if what was actually asked is as
    visible as what came back; a caller that printed only the answer
    would be asking the owner to trust a sentence with no way to
    check what produced it, the same failure this heritage already
    refused for a log-signature `RuntimeFinding` with no evidence
    (`STD-0300` § VS-4 criterion 4.9).

    **Not a `RuntimeFinding`, and not cited as evidence by one.** A
    `RuntimeFinding` states what a governed rule or correlation
    observed; this states what a language model said about one,
    after the fact, and is not itself grounded in anything the model
    did not already read in its own prompt. Keeping the two types
    separate is what keeps AI Runtime output from being mistaken for
    something the deterministic Runtime vouched for.

    **`reachable`/`unreachable_reason` mirror
    `aistack.ai_runtime.engine.AIEngine.complete`'s own return shape**
    — an engine that could not be reached is a real, reportable
    outcome (`FDN-0003` Article 12), not an exception a caller has to
    catch.

    **`language` names what `response` was asked to be in, not a
    verified fact about the text itself** — `aistack.ai_runtime
    .operations`'s own `target_language`, 2026-09-27. When that
    module's translation pass ran and produced text, `response` is
    genuinely in this language; when no translator was configured, or
    the translation call itself failed, `response` is left exactly as
    the reasoning model gave it and `language` still names what was
    requested, not what `response` provably is — the same honest gap
    `unreachable_reason` already names for the engine itself, one
    layer further out. Defaults to `"fr"`, the original, only
    language this ever asked for before 2026-09-27.
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
