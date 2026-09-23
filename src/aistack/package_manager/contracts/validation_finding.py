"""
Package Manager — ValidationFinding contract.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    """
    The outcome of validating one PackageItem.

    `passed=False` blocks integration of the whole package —
    `ARCH-0013`: "Validation and integration must remain separate
    capabilities" and "the validation phase must precede integration."
    A partially-valid package is not integrated a la carte; the
    Package Manager reports every finding so a reviewer sees the whole
    picture at once, but integration is all-or-nothing per package.
    """

    target_path: str

    passed: bool

    message: str
