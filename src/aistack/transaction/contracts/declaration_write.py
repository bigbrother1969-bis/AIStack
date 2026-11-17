"""Knowledge Transaction - the payload of a `declaration.write` operation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

KIND = "declaration.write"


@dataclass(frozen=True, slots=True)
class DeclarationWrite:
    """
    One declaration written whole: where, what and on whose behalf.

    `content` is the complete text of the file. `author` and `reason`
    are kept with the change (`aistack.declaration`); neither may carry
    a secret, the change is recorded (`ADR-0027` § 11).
    """

    path: Path
    content: str
    author: str
    reason: str
