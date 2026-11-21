"""A free question from a person, as the AI Runtime is asked it (`portal.chat`, ADR-0029 § 12)."""

from __future__ import annotations

from dataclasses import dataclass

SUBJECT = "question"
OPERATION = "ask"
MAX_LENGTH = 2000


@dataclass(frozen=True)
class Question:
    """
    What a person typed. It is held in memory for the length of the answer and never written: the
    journal of calls names the engine and the reason, never a word of it.
    """

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("a question has a text")

        if len(self.text) > MAX_LENGTH:
            raise ValueError(f"a question is at most {MAX_LENGTH} characters long")

    @property
    def subject(self) -> str:
        return SUBJECT

    @property
    def signature(self) -> str:
        return "portal.chat"

    @property
    def interpretation(self) -> str:
        return self.text.strip()

    @property
    def remediation(self) -> str:
        return "none"

    @property
    def confidence(self) -> str:
        return "asked"

    @property
    def qualifications(self) -> tuple[str, ...]:
        return ()
