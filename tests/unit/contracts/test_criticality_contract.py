from aistack.contracts.criticality import CriticalityLevel


def test_criticality_levels_exist():

    assert CriticalityLevel.C1 == 1
    assert CriticalityLevel.C2 == 2
    assert CriticalityLevel.C3 == 3


def test_criticality_order():

    assert CriticalityLevel.C3 > CriticalityLevel.C2
    assert CriticalityLevel.C2 > CriticalityLevel.C1
