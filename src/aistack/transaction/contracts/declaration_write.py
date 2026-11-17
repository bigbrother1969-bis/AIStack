"""Knowledge Transaction - the payload of a `declaration.write` operation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

KIND = "declaration.write"


@dataclass(frozen=True, slots=True)
class DeclarationWrite:
    """
    One declaration written whole: where, what and on whose behalf.

    `content` is the complete text of the file, or `None` to take the file
    away (the previous one is kept all the same). `copy_label`, when given, is
    part of the kept copy's name (`<name>.avant-<label>-<date>-<time>`).
    `author` and `reason` are kept with the change (`aistack.declaration`);
    neither may carry a secret, the change is recorded (`ADR-0027` § 11).
    """

    path: Path
    content: str | None
    author: str
    reason: str
    copy_label: str = ""
