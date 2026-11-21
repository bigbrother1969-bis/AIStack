"""
The principles of `FDN-0012` as the "Governed Heritage Engineering" page lists them: identifier and
criticality, in the registry's order. The titles are in the catalogs (`ghe.principle.<id>`); a test
holds this list and the English titles to the registry, so the page cannot drift from it.
"""

from __future__ import annotations

FAMILIES = ("FDN", "GOV", "ARC", "STD", "ENG", "OPS")

PRINCIPLES: tuple[tuple[str, str], ...] = (
    ("FDN-P-001", "C3"),
    ("FDN-P-002", "C3"),
    ("FDN-P-003", "C3"),
    ("FDN-P-004", "C3"),
    ("FDN-P-005", "C3"),
    ("FDN-P-006", "C3"),
    ("FDN-P-007", "C3"),
    ("FDN-P-008", "C3"),
    ("FDN-P-009", "C3"),
    ("FDN-P-010", "C3"),
    ("FDN-P-011", "C3"),
    ("FDN-P-012", "C3"),
    ("FDN-P-013", "C3"),
    ("FDN-P-014", "C3"),
    ("FDN-P-015", "C3"),
    ("GOV-P-001", "C3"),
    ("GOV-P-002", "C2"),
    ("GOV-P-003", "C2"),
    ("GOV-P-004", "C2"),
    ("GOV-P-005", "C2"),
    ("GOV-P-006", "C2"),
    ("ARC-P-001", "C3"),
    ("ARC-P-002", "C3"),
    ("ARC-P-003", "C3"),
    ("ARC-P-004", "C3"),
    ("ARC-P-005", "C2"),
    ("ARC-P-006", "C2"),
    ("ARC-P-007", "C2"),
    ("ARC-P-008", "C2"),
    ("ARC-P-009", "C2"),
    ("ARC-P-010", "C2"),
    ("ARC-P-011", "C2"),
    ("ARC-P-012", "C3"),
    ("ARC-P-013", "C2"),
    ("ARC-P-014", "C2"),
    ("STD-P-001", "C2"),
    ("STD-P-002", "C2"),
    ("STD-P-003", "C2"),
    ("STD-P-004", "C2"),
    ("STD-P-005", "C2"),
    ("ENG-P-001", "C2"),
    ("ENG-P-002", "C2"),
    ("ENG-P-003", "C2"),
    ("ENG-P-004", "C2"),
    ("ENG-P-005", "C2"),
    ("ENG-P-006", "C1"),
    ("ENG-P-007", "C2"),
    ("OPS-P-001", "C2"),
    ("OPS-P-002", "C2"),
    ("OPS-P-003", "C1"),
    ("OPS-P-004", "C2"),
)

ARTICLES = 18


def of_family(family: str) -> tuple[tuple[str, str], ...]:
    """The principles of one family, in the registry's order."""

    return tuple(item for item in PRINCIPLES if item[0].startswith(f"{family}-"))
