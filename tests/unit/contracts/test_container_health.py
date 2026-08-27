import pytest

from aistack.contracts.container_health import (
    ContainerHealth,
    health_of,
)


# --------------------------------------------------------------------
# The defect this exists to end
# --------------------------------------------------------------------


def test_a_container_with_no_healthcheck_is_not_healthy():
    """
    The whole reason for this module. The experimenter ADR-0009
    retired computed `health.get("Status", "healthy")`, so a
    container declaring no healthcheck was displayed as sound.

    Measured 2026-08-27 on the reference deployment: 44 of 61
    containers are in this case. FDN-0003 Article 12 — *AIStack
    shall never replace missing knowledge with unsupported
    assumptions.*
    """

    assert health_of("Up 3 days") is ContainerHealth.UNDECLARED

    assert health_of("Up 3 days") is not ContainerHealth.HEALTHY


def test_an_absent_status_is_not_healthy_either():
    """
    The same default, one layer up: a container the collection
    returned without a `Status` at all.
    """

    assert health_of(None) is ContainerHealth.UNDECLARED
    assert health_of("") is ContainerHealth.UNDECLARED


# --------------------------------------------------------------------
# What a status declares
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, expected",
    [
        ("Up 2 hours (healthy)", ContainerHealth.HEALTHY),
        ("Up 5 minutes (unhealthy)", ContainerHealth.UNHEALTHY),
        ("Up 30 seconds (health: starting)", ContainerHealth.STARTING),
        ("Up 30 seconds (health:starting)", ContainerHealth.STARTING),
        ("Up 3 days", ContainerHealth.UNDECLARED),
        ("Created", ContainerHealth.UNDECLARED),
        ("Restarting (1) 4 seconds ago", ContainerHealth.UNDECLARED),
    ],
)
def test_what_a_docker_status_declares(status, expected):

    assert health_of(status) is expected


def test_an_exit_code_is_not_a_health_verdict():
    """
    `Status` carries parentheses that say nothing about health,
    and the common one is an exit code. A parser matching any
    parenthetical would read `Exited (0)` as a declared state and
    then have to decide what `0` means about health — which is a
    question Docker never asked.

    This is why the three literals are matched rather than the
    shape.
    """

    assert health_of("Exited (0) 2 days ago") is ContainerHealth.UNDECLARED
    assert health_of("Exited (137) 1 hour ago") is ContainerHealth.UNDECLARED


# --------------------------------------------------------------------
# The fourth state
# --------------------------------------------------------------------


def test_starting_is_neither_healthy_nor_unhealthy_nor_undeclared():
    """
    **The member that made this a separate act**, decided
    2026-08-27 by the owner.

    A container in `health: starting` has a healthcheck — so
    `UNDECLARED` would deny something that exists — and has no
    verdict — so `UNHEALTHY` would state one nobody reached.
    Article 12 forbids both directions.

    It was measured to be absent at the instant it was decided:
    44 undeclared, 17 healthy, zero starting. It is transitory by
    construction, and every one of the seventeen passes through it
    on each restart.
    """

    starting = health_of("Up 10 seconds (health: starting)")

    assert starting is ContainerHealth.STARTING

    assert starting is not ContainerHealth.UNDECLARED
    assert starting is not ContainerHealth.HEALTHY
    assert starting is not ContainerHealth.UNHEALTHY


def test_starting_is_a_declaration_and_undeclared_is_not():
    """
    The distinction the fourth member buys, stated as the
    predicate a consumer reads rather than as an enum comparison.
    """

    assert health_of("Up 10 seconds (health: starting)").is_declared
    assert health_of("Up 2 hours (healthy)").is_declared
    assert health_of("Up 5 minutes (unhealthy)").is_declared

    assert not health_of("Up 3 days").is_declared


def test_the_vocabulary_is_four_and_says_so():
    """
    A guard on the act rather than on the code. ADR-0009 § 6
    named three states until v1.8; a fifth arriving without the
    same deliberation would widen a governed vocabulary by
    accident.
    """

    assert {member.value for member in ContainerHealth} == {
        "healthy",
        "unhealthy",
        "starting",
        "undeclared",
    }


def test_the_verdict_is_the_parenthetical_and_not_the_word():
    """
    **Asserted as a boundary, not from an observed defect**, and
    labelled so rather than dressed as a bug report. No `docker
    ps` output known on 2026-08-27 prints these words outside
    their parentheses.

    It exists because the mutation pass found the parentheses
    unwatched: removing them from the pattern left every other
    test in this file green. Between dropping them as unearned
    and stating what they mean, this states what they mean —
    loose reading is the subject of this module. Docker delimits
    the verdict; this reads the delimiters. A word appearing
    somewhere in a sentence is not a runtime declaring anything.
    """

    assert health_of("Up 2 hours, healthy") is ContainerHealth.UNDECLARED
    assert health_of("unhealthy") is ContainerHealth.UNDECLARED
    assert health_of("health: starting") is ContainerHealth.UNDECLARED
