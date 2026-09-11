import pytest

from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading


def test_a_reading_names_its_container():

    with pytest.raises(ValueError, match="names none"):
        ContainerStateReading(
            container="", state="running", health=ContainerHealth.HEALTHY
        )


def test_a_reading_refuses_an_empty_state():

    with pytest.raises(ValueError, match="no state at all"):
        ContainerStateReading(
            container="gluetun", state="", health=ContainerHealth.UNDECLARED
        )


def test_a_reading_carries_state_and_health_independently():

    reading = ContainerStateReading(
        container="gluetun", state="restarting", health=ContainerHealth.UNDECLARED
    )

    assert reading.state == "restarting"
    assert reading.health is ContainerHealth.UNDECLARED
