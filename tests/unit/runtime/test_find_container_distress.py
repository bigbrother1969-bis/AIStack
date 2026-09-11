from aistack.contracts.container_distress import RESTARTING, UNHEALTHY
from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.runtime.container_distress import find_container_distress


def reading(
    container: str, state: str, health: ContainerHealth
) -> ContainerStateReading:
    return ContainerStateReading(container=container, state=state, health=health)


def test_a_restarting_container_is_flagged():

    distress = find_container_distress(
        [reading("gluetun", "restarting", ContainerHealth.UNDECLARED)]
    )

    assert len(distress) == 1
    assert distress[0].reasons == (RESTARTING,)


def test_an_unhealthy_container_is_flagged():

    distress = find_container_distress(
        [reading("gluetun", "running", ContainerHealth.UNHEALTHY)]
    )

    assert len(distress) == 1
    assert distress[0].reasons == (UNHEALTHY,)


def test_a_container_that_is_both_restarting_and_unhealthy_carries_both_reasons():

    distress = find_container_distress(
        [reading("gluetun", "restarting", ContainerHealth.UNHEALTHY)]
    )

    assert len(distress) == 1
    assert set(distress[0].reasons) == {RESTARTING, UNHEALTHY}


def test_a_running_healthy_container_is_not_flagged():

    distress = find_container_distress(
        [reading("gluetun", "running", ContainerHealth.HEALTHY)]
    )

    assert distress == ()


def test_a_starting_container_is_never_flagged():
    """
    ADR-0009 § 6: `STARTING` is transitory by construction, during a
    container's own `--start-period`. Flagging it would be exactly
    the conflation the fourth `ContainerHealth` state was added to
    prevent.
    """

    distress = find_container_distress(
        [reading("gluetun", "running", ContainerHealth.STARTING)]
    )

    assert distress == ()


def test_an_undeclared_health_alone_is_never_flagged():
    """
    FDN-0003 Article 12: no healthcheck declared states no verdict at
    all — never a verdict nobody reached.
    """

    distress = find_container_distress(
        [reading("gluetun", "running", ContainerHealth.UNDECLARED)]
    )

    assert distress == ()


def test_an_exited_container_with_no_healthcheck_is_not_flagged():
    """
    Only `restarting`/`unhealthy` are in scope — a stopped container
    is a different, ungoverned-by-this-function state.
    """

    distress = find_container_distress(
        [reading("gluetun", "exited", ContainerHealth.UNDECLARED)]
    )

    assert distress == ()


def test_only_the_containers_in_distress_are_flagged_in_a_batch():

    readings = [
        reading("gluetun", "restarting", ContainerHealth.UNDECLARED),
        reading("jellyfin", "running", ContainerHealth.HEALTHY),
        reading("beszel", "running", ContainerHealth.UNHEALTHY),
    ]

    distress = find_container_distress(readings)

    assert {d.reading.container for d in distress} == {"gluetun", "beszel"}


def test_an_empty_reading_set_flags_nothing():

    assert find_container_distress([]) == ()
