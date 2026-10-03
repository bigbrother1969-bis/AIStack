"""
What a finding says, as catalog keys rather than finished sentences
(ADR-0010 § 4, revised 2026-10-03).

A `RuntimeFinding` keeps its English `interpretation` and
`remediation` — they are what the AI Runtime is prompted with, what
the reasoning history records and what the CLIs print, "copied from
the signature at the moment of qualification". Beside them, an
evaluator that knows its own sentences can attach a `FindingMessage`:
the same sentences as catalog keys and the values that fill them, so a
page renders them in the reader's language. Each English catalog entry
renders to exactly the evaluator's own English text — the suite holds
the two to the same words.

A sentence is a sequence of parts joined by a space: some evaluators
build theirs from a statement and optional clauses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MessagePart:
    """One catalog key and the values its placeholders take."""

    key: str
    params: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("a message part names no catalog key")


@dataclass(frozen=True)
class FindingMessage:
    """The interpretation and the remediation, part by part."""

    interpretation: tuple[MessagePart, ...]
    remediation: tuple[MessagePart, ...]

    def __post_init__(self) -> None:
        if not self.interpretation or not self.remediation:
            raise ValueError("a finding message carries both an interpretation and a remediation")


def part(key: str, **params: object) -> MessagePart:
    """A `MessagePart`, its values already formatted by the caller."""

    return MessagePart(key=key, params=tuple((name, str(value)) for name, value in params.items()))
