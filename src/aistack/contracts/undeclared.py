"""
The sentinel for a value a human has not declared.

An undeclared value is a visible state, never replaced by a plausible
default. All qualifications share this one definition.
"""

UNDECLARED = "unknown"


def is_declared(value: str) -> bool:
    """True when a human has declared this value."""

    return value != UNDECLARED
