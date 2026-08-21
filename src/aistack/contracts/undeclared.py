"""
The governed representation of what an artifact has not said.

FDN-0003 Article 12 makes an undeclared value a *state of the
heritage*, not a missing field and not an error. It must stay
visible, and it must never be replaced by a plausible default.

The sentinel lives here, alone, because it belongs to no single
qualification. Criticality, domain, semantic type, ownership and
lifecycle all share it, and a value that means "the human has not
said" must have exactly one definition — otherwise the meaning
drifts one copy at a time.
"""

UNDECLARED = "unknown"


def is_declared(value: str) -> bool:
    """
    True when a human has declared this value.
    """

    return value != UNDECLARED
