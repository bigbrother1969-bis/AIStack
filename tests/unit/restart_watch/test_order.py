from __future__ import annotations

from conftest import container

from aistack.restart_watch.order import plan_restart


def test_a_provider_is_restarted_before_what_shares_its_network():
    facts = [
        container("gluetun", health="unhealthy"),
        container("qbittorrent", provider="gluetun"),
        container("mularr", provider="gluetun"),
    ]

    plan = plan_restart({"gluetun"}, facts)

    assert plan.order == ("gluetun", "mularr", "qbittorrent")
    assert plan.dragged == ("mularr", "qbittorrent")


def test_a_stuck_dependent_alone_drags_nothing_and_leaves_its_provider():
    facts = [container("gluetun", started=40), container("qbittorrent", started=20, provider="gluetun")]

    plan = plan_restart({"qbittorrent"}, facts)

    assert plan.order == ("qbittorrent",)
    assert plan.dragged == ()


def test_compose_dependencies_order_the_restart():
    facts = [
        container("app", depends_on=("db",)),
        container("db"),
    ]

    assert plan_restart({"app", "db"}, facts).order == ("db", "app")


def test_the_owner_s_exceptions_decide_what_docker_cannot_say():
    facts = [container("firefly"), container("firefly_db")]

    assert plan_restart({"firefly", "firefly_db"}, facts).order == ("firefly", "firefly_db")
    assert plan_restart({"firefly", "firefly_db"}, facts, {"firefly": ["firefly_db"]}).order == (
        "firefly_db",
        "firefly",
    )


def test_a_loop_is_ordered_by_name_and_flagged():
    facts = [container("a", depends_on=("b",)), container("b", depends_on=("a",))]

    plan = plan_restart({"a", "b"}, facts)

    assert plan.order == ("a", "b")
    assert plan.cycle is True


def test_the_same_situation_always_gives_the_same_order():
    facts = [container(name) for name in ("z", "m", "a")]

    assert plan_restart({"z", "m", "a"}, facts).order == ("a", "m", "z")


def test_never_and_unknown_names_are_dropped():
    facts = [container("a"), container("b")]

    assert plan_restart({"a", "b", "ghost"}, facts, never=["b"]).order == ("a",)
