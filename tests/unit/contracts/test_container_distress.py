import pytest

from aistack.contracts.container_distress import (
    RESTARTING,
    UNHEALTHY,
    ContainerDistress,
)
from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading


def restarting_reading(container: str = "gluetun") -> ContainerStateReading:
    return ContainerStateReading(
        container=container, state="restarting", health=ContainerHealth.UNDECLARED
    )


def unhealthy_reading(container: str = "gluetun") -> ContainerStateReading:
    return ContainerStateReading(
        container=container, state="running", health=ContainerHealth.UNHEALTHY
    )


def test_a_distress_naming_no_reason_is_refused():

    with pytest.raises(ValueError, match="names no reason"):
        ContainerDistress(reading=restarting_reading(), reasons=())


def test_a_distress_refuses_a_repeated_reason():

    with pytest.raises(ValueError, match="same reason more than once"):
        ContainerDistress(
            reading=restarting_reading(), reasons=(RESTARTING, RESTARTING)
        )


def test_a_distress_refuses_an_unknown_reason():

    with pytest.raises(ValueError, match=r"only .* are detected"):
        ContainerDistress(reading=restarting_reading(), reasons=("oom-killed",))


def test_restarting_is_refused_when_the_reading_does_not_say_so():

    with pytest.raises(ValueError, match="cites 'restarting'"):
        ContainerDistress(reading=unhealthy_reading(), reasons=(RESTARTING,))


def test_unhealthy_is_refused_when_the_reading_does_not_say_so():

    with pytest.raises(ValueError, match="cites 'unhealthy'"):
        ContainerDistress(reading=restarting_reading(), reasons=(UNHEALTHY,))


def test_a_restarting_reading_accepts_the_restarting_reason():

    distress = ContainerDistress(reading=restarting_reading(), reasons=(RESTARTING,))

    assert distress.reasons == (RESTARTING,)


def test_an_unhealthy_reading_accepts_the_unhealthy_reason():

    distress = ContainerDistress(reading=unhealthy_reading(), reasons=(UNHEALTHY,))

    assert distress.reasons == (UNHEALTHY,)


def test_a_container_may_carry_both_reasons_at_once():

    reading = ContainerStateReading(
        container="gluetun", state="restarting", health=ContainerHealth.UNHEALTHY
    )

    distress = ContainerDistress(reading=reading, reasons=(RESTARTING, UNHEALTHY))

    assert set(distress.reasons) == {RESTARTING, UNHEALTHY}
