"""
What counts as stuck (ADR-0025 § 2). The cases are the ones measured on
the MSI on 2026-11-15, after a cold boot: Firefly unhealthy, Scrutiny up
with no web server, qBittorrent and Mularr on a stale gluetun network.
"""

from __future__ import annotations

from conftest import container

from aistack.restart_watch.detect import PROBE_FAILED, STALE_NETWORK, UNHEALTHY, find_stuck


def test_an_unhealthy_container_is_stuck():
    stuck = find_stuck([container("firefly", health="unhealthy")])

    assert [(s.name, s.reasons) for s in stuck] == [("firefly", (UNHEALTHY,))]


def test_a_container_still_starting_or_healthy_is_left_alone():
    assert find_stuck([container("a", health="starting"), container("b", health="healthy")]) == ()


def test_a_dependent_older_than_its_network_provider_is_stale():
    facts = [
        container("gluetun", started=40, health="healthy"),
        container("qbittorrent", started=20, provider="gluetun"),
        container("mularr", started=21, provider="gluetun"),
    ]

    assert [(s.name, s.reasons) for s in find_stuck(facts)] == [
        ("mularr", (STALE_NETWORK,)),
        ("qbittorrent", (STALE_NETWORK,)),
    ]


def test_a_dependent_started_after_or_with_its_provider_is_not_stale():
    facts = [
        container("gluetun", started=20),
        container("after", started=30, provider="gluetun"),
        container("same-second", started=19, provider="gluetun"),
    ]

    assert find_stuck(facts) == ()


def test_a_declared_probe_that_failed_names_a_container_without_healthcheck():
    facts = [container("scrutiny"), container("with-check", health="healthy")]

    stuck = find_stuck(facts, failed_probes={"scrutiny", "with-check"})

    assert [(s.name, s.reasons) for s in stuck] == [("scrutiny", (PROBE_FAILED,))]


def test_a_stopped_container_is_never_stuck():
    facts = [container("comfyui", running=False, health="unhealthy")]

    assert find_stuck(facts) == ()


def test_the_never_list_and_the_watch_itself_are_left_alone():
    facts = [
        container("keep", health="unhealthy"),
        container("aistack-restart-watch", health="unhealthy"),
    ]

    assert find_stuck(facts, never=["keep"]) == ()


def test_reasons_add_up():
    facts = [
        container("gluetun", started=40),
        container("both", started=20, health="unhealthy", provider="gluetun"),
    ]

    assert find_stuck(facts)[0].reasons == (UNHEALTHY, STALE_NETWORK)
