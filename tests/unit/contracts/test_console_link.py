import pytest

from aistack.contracts.console_link import LAN, PUBLIC, ConsoleLink


def test_a_link_names_no_service_is_refused():
    with pytest.raises(ValueError, match="names no service"):
        ConsoleLink(name="", description="x", url="http://GIGABYTE:8181", scope=LAN)


def test_a_link_with_no_description_is_refused():
    with pytest.raises(ValueError, match="declares no description"):
        ConsoleLink(
            name="Selection UI", description="", url="http://GIGABYTE:8181", scope=LAN
        )


def test_a_link_with_no_url_is_refused():
    with pytest.raises(ValueError, match="declares no url"):
        ConsoleLink(name="Selection UI", description="x", url="", scope=LAN)


def test_a_url_with_an_unreachable_scheme_is_refused():
    with pytest.raises(ValueError, match="cannot link to"):
        ConsoleLink(
            name="Selection UI",
            description="x",
            url="ftp://GIGABYTE:8181",
            scope=LAN,
        )


def test_an_absolute_http_url_is_accepted():
    link = ConsoleLink(
        name="Selection UI", description="x", url="http://GIGABYTE:8181", scope=LAN
    )

    assert link.url == "http://GIGABYTE:8181"


def test_an_absolute_https_url_is_accepted():
    link = ConsoleLink(
        name="Console",
        description="x",
        url="https://aistack.persiaut-family.fr",
        scope=PUBLIC,
    )

    assert link.url == "https://aistack.persiaut-family.fr"


def test_a_relative_url_is_accepted():
    link = ConsoleLink(
        name="Cockpit Santé", description="x", url="/health.html", scope=PUBLIC
    )

    assert link.url == "/health.html"


# --------------------------------------------------------------------
# scope (added 2026-09-30, the owner's "bandeau de couleur différent
# pour les cartes accessibles sur le réseau local ou depuis internet")
# --------------------------------------------------------------------


def test_a_link_with_no_scope_is_refused():
    with pytest.raises(ValueError, match="declares a scope this console does not know"):
        ConsoleLink(
            name="Selection UI", description="x", url="http://GIGABYTE:8181", scope=""
        )


def test_a_link_with_an_unknown_scope_is_refused():
    with pytest.raises(ValueError, match="declares a scope this console does not know"):
        ConsoleLink(
            name="Selection UI",
            description="x",
            url="http://GIGABYTE:8181",
            scope="internet",
        )


def test_a_lan_scope_is_accepted():
    link = ConsoleLink(
        name="Selection UI", description="x", url="http://GIGABYTE:8181", scope=LAN
    )

    assert link.scope == "lan"


def test_a_public_scope_is_accepted():
    link = ConsoleLink(
        name="Cockpit Santé", description="x", url="/health.html", scope=PUBLIC
    )

    assert link.scope == "public"
