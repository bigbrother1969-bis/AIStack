"""What the host exposes, read from the kernel's tables and Docker, and judged (ADR-0028 T1)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from aistack.security.definition import SecurityDefinition
from aistack.security.exposure import (
    ALL,
    LOOPBACK,
    SPECIFIC,
    Listener,
    Published,
    assess,
    merge,
    parse_published,
    parse_sockets,
    read_listeners,
    read_published,
)
from aistack.security.findings import FIX, INFORMATION, WATCH

HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"


def _tcp(*rows: tuple[str, str]) -> str:
    return HEADER + "".join(
        f"   {index}: {local} 00000000:0000 {state} 00000000:00000000 00:00000000 00000000     0        0 1\n"
        for index, (local, state) in enumerate(rows)
    )


def test_a_listening_tcp_socket_is_read_with_its_reach() -> None:
    text = _tcp(
        ("00000000:1F90", "0A"),  # 0.0.0.0:8080
        ("0100007F:0016", "0A"),  # 127.0.0.1:22
        ("0A01A8C0:01BB", "0A"),  # 192.168.1.10:443
    )

    assert parse_sockets("tcp", text) == [
        Listener("tcp", 8080, ALL),
        Listener("tcp", 22, LOOPBACK),
        Listener("tcp", 443, SPECIFIC),
    ]


def test_only_listening_sockets_count() -> None:
    text = _tcp(("00000000:1F90", "01"), ("00000000:0050", "0A"))  # established, then listening

    assert parse_sockets("tcp", text) == [Listener("tcp", 80, ALL)]


def test_a_bound_udp_socket_counts_and_an_unbound_one_does_not() -> None:
    text = _tcp(("00000000:0035", "07"), ("00000000:0044", "01"))

    assert parse_sockets("udp", text) == [Listener("udp", 53, ALL)]


def test_ipv6_addresses_are_read() -> None:
    wide = "00000000000000000000000000000000:0050"
    loopback = "00000000000000000000000001000000:0051"

    assert parse_sockets("tcp", _tcp((wide, "0A"), (loopback, "0A"))) == [
        Listener("tcp", 80, ALL),
        Listener("tcp", 81, LOOPBACK),
    ]


def test_a_line_that_cannot_be_read_is_skipped() -> None:
    text = HEADER + "garbage\n   0: ZZ:ZZ 00000000:0000 0A\n   1: 00000000:0000 00000000:0000 0A\n"

    assert parse_sockets("tcp", text) == []


def test_ipv4_and_ipv6_merge_at_the_widest_reach() -> None:
    merged = merge([Listener("tcp", 80, LOOPBACK), Listener("tcp", 80, ALL), Listener("udp", 80, SPECIFIC)])

    assert merged == [Listener("tcp", 80, ALL), Listener("udp", 80, SPECIFIC)]


def test_the_tables_are_read_and_a_missing_one_is_named(tmp_path: Path) -> None:
    (tmp_path / "tcp").write_text(_tcp(("00000000:0050", "0A")), encoding="ascii")
    (tmp_path / "tcp6").write_text(_tcp(("00000000000000000000000000000000:0050", "0A")), encoding="ascii")
    (tmp_path / "udp").write_text(_tcp(("00000000:0035", "07")), encoding="ascii")

    listeners, unread = read_listeners(tmp_path)

    assert listeners == [Listener("tcp", 80, ALL), Listener("udp", 53, ALL)]
    assert unread == ["udp6"]


def _ps(*entries: dict[str, str]) -> str:
    return "\n".join(json.dumps(entry) for entry in entries)


def test_published_ports_are_read_with_their_owner_and_reach() -> None:
    text = _ps(
        {"Names": "web", "Ports": "0.0.0.0:8098->8000/tcp, :::8098->8000/tcp"},
        {"Names": "db", "Ports": "127.0.0.1:5432->5432/tcp"},
        {"Names": "lan", "Ports": "192.168.1.10:9000->9000/udp, 80/tcp"},
        {"Names": "range", "Ports": "0.0.0.0:7000-7002->7000-7002/tcp"},
        {"Names": "none", "Ports": ""},
    )

    published = parse_published(text + "\nnot json\n[1]")

    assert Published("web", "tcp", 8098, ALL) in published
    assert Published("db", "tcp", 5432, LOOPBACK) in published
    assert Published("lan", "udp", 9000, SPECIFIC) in published
    assert [item.port for item in published if item.container == "range"] == [7000, 7001, 7002]
    assert all(item.container != "none" for item in published)


def test_docker_is_asked_with_a_read_only_command() -> None:
    seen: list[list[str]] = []

    def run(command, **_):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=_ps({"Names": "a", "Ports": "0.0.0.0:80->80/tcp"}), stderr="")

    assert read_published(run) == [Published("a", "tcp", 80, ALL)]
    assert seen == [["docker", "ps", "--format", "{{json .}}"]]


def test_docker_that_cannot_be_asked_is_none_not_empty() -> None:
    def missing(command, **_):
        raise FileNotFoundError("docker")

    def failing(command, **_):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="denied")

    assert read_published(missing) is None
    assert read_published(failing) is None


def _keys(findings) -> list[str]:
    return [finding.key for finding in findings]


def test_the_firewall_is_always_said_not_read() -> None:
    findings = assess([], [], [], SecurityDefinition())

    firewall = [item for item in findings if item.key == "firewall.not_read"]
    assert len(firewall) == 1
    assert firewall[0].severity == INFORMATION and firewall[0].unknown


def test_a_critical_port_on_every_interface_is_to_fix() -> None:
    definition = SecurityDefinition(critical_ports={2375: "Docker API (no TLS)"})

    findings = assess([Listener("tcp", 2375, ALL)], [], [], definition)

    critical = [item for item in findings if item.key == "exposure.critical.tcp.2375"]
    assert critical and critical[0].severity == FIX


def test_a_sensitive_port_on_every_interface_is_to_watch_and_names_its_container() -> None:
    definition = SecurityDefinition(sensitive_ports={5432: "PostgreSQL"})
    published = [Published("immich_postgres", "tcp", 5432, ALL)]

    findings = assess([Listener("tcp", 5432, ALL)], [], published, definition)

    sensitive = [item for item in findings if item.key == "exposure.sensitive.tcp.5432"]
    assert sensitive and sensitive[0].severity == WATCH
    assert sensitive[0].evidence == ("5432/tcp (immich_postgres)",)


def test_a_declared_port_is_no_longer_reported() -> None:
    definition = SecurityDefinition(
        declared_ports={22: "SSH", 8080: "web"}, sensitive_ports={22: "SSH"}
    )

    findings = assess([Listener("tcp", 22, ALL), Listener("tcp", 8080, ALL)], [], [], definition)

    assert _keys(findings) == ["firewall.not_read"]


def test_a_port_reached_only_from_the_host_is_not_reported() -> None:
    definition = SecurityDefinition(critical_ports={2375: "Docker API"})

    findings = assess([Listener("tcp", 2375, LOOPBACK), Listener("tcp", 9000, SPECIFIC)], [], [], definition)

    assert _keys(findings) == ["firewall.not_read"]


def test_undeclared_ports_make_one_finding_that_is_bounded() -> None:
    listeners = [Listener("tcp", 9000 + index, ALL) for index in range(30)]

    findings = assess(listeners, [], [], SecurityDefinition(max_listed=5))

    undeclared = [item for item in findings if item.key == "exposure.undeclared_on_all_interfaces"]
    assert len(undeclared) == 1 and undeclared[0].severity == WATCH
    assert undeclared[0].title.startswith("30 port(s)")
    assert undeclared[0].evidence[-1] == "and 25 more" and len(undeclared[0].evidence) == 6


def test_a_declared_port_with_nothing_listening_is_information() -> None:
    findings = assess([], [], [], SecurityDefinition(declared_ports={8080: "web"}))

    missing = [item for item in findings if item.key == "exposure.declared_not_listening"]
    assert missing and missing[0].severity == INFORMATION and missing[0].evidence == ("8080 (web)",)


def test_what_could_not_be_read_is_a_finding_never_an_absence() -> None:
    findings = assess([], ["udp6"], None, SecurityDefinition())

    assert "exposure.sockets_unreadable" in _keys(findings)
    assert "exposure.docker_unreadable" in _keys(findings)
