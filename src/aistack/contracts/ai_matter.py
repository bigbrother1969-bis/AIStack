"""What a model is asked about: the six facts a prompt of the AI Runtime states."""

from __future__ import annotations

from typing import Protocol


class AIMatter(Protocol):
    """
    The matter of a question to a model, as the operations of the AI Runtime read it.

    A `RuntimeFinding` is one (a rule's qualified finding); so is a free `Question` from a person.
    Read-only: an operation never changes what it is asked about.
    """

    @property
    def subject(self) -> str: ...

    @property
    def signature(self) -> str: ...

    @property
    def interpretation(self) -> str: ...

    @property
    def remediation(self) -> str: ...

    @property
    def confidence(self) -> str: ...

    @property
    def qualifications(self) -> tuple[str, ...]: ...
