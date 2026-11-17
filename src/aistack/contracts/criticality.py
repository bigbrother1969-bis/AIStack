from enum import IntEnum

from aistack.contracts.undeclared import UNDECLARED


class CriticalityLevel(IntEnum):

    C1 = 1
    C2 = 2
    C3 = 3


def normalize_criticality(value) -> str:
    """
    Return a declared criticality in canonical form, or
    "unknown".

    Criticality is a qualification. Per FDN-0003 Article 4 it
    is a human contribution: this function reads a
    declaration, it never infers one. A value that is absent,
    empty or outside the governed levels is reported as
    undeclared rather than guessed.
    """

    if value is None:
        return UNDECLARED

    text = str(value).strip().upper()

    if not text:
        return UNDECLARED

    if text.startswith("C"):
        text = text[1:]

    try:
        level = CriticalityLevel(int(text))

    except (ValueError, TypeError):
        return UNDECLARED

    return level.name
