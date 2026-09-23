"""
Package Manager — PackageItem contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PackageItem:
    """
    One proposed change carried by a KnowledgePackage.

    `ARCH-0013`'s Open Points leave "exact PackageManager interfaces"
    and "integration conflict resolution rules" undecided. This first
    item shape does not resolve them in the abstract — it states the
    proposed change explicitly (target path, anchor, content) rather
    than inferring where knowledge belongs, the same restraint
    `FDN-0003` Article 12 asks for when the answer is not yet known.

    `target_path` is a path relative to the repository root.

    `anchor`, when not `None`, must match exactly one line of the
    target file's current content — the same uniqueness discipline as
    a text replacement: an anchor that matches zero or more than one
    line is a validation failure, never a guess at which one was
    meant. `None` means "the end of the file."

    `position` says whether `content` is inserted immediately before
    or after the anchor line. Ignored when `anchor` is `None` — content
    is always appended at the end in that case.

    `rationale` is a short, human-readable explanation of why this
    change is proposed — carried through Inspection and Validation so
    a reviewer never has to guess intent from a diff alone.
    """

    target_path: str

    content: str

    rationale: str

    anchor: str | None = None

    position: Literal["before", "after"] = "after"
