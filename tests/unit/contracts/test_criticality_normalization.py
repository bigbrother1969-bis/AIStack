from aistack.contracts.undeclared import UNDECLARED, is_declared
from aistack.contracts.criticality import (
    CriticalityLevel,
    normalize_criticality,
)


def test_governed_levels_are_normalized():

    for value in ("C3", "c3", 3, "3", " C2 "):
        assert normalize_criticality(value) in {
            CriticalityLevel.C2.name,
            CriticalityLevel.C3.name,
        }

    assert normalize_criticality("c1") == "C1"


def test_absent_declaration_is_unknown():
    """
    Article 12: an absent qualification is a governed state,
    never a guessed value.
    """

    assert normalize_criticality(None) == UNDECLARED
    assert normalize_criticality("") == UNDECLARED
    assert normalize_criticality("   ") == UNDECLARED


def test_value_outside_the_governed_levels_is_unknown():
    """
    A malformed declaration is not a declaration. C4 is not a
    level AIStack governs, so it states nothing.
    """

    for value in ("C4", "C0", 0, 4, "banana", "CX"):
        assert normalize_criticality(value) == UNDECLARED


def test_is_declared():

    assert is_declared("C3")
    assert not is_declared(UNDECLARED)
