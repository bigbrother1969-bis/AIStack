"""The firewall read from a host snapshot: from where can a port be reached (ADR-0028 T1b)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.security.definition import SecurityDefinition
from aistack.security.exposure import ALL, Listener, Published, assess
from aistack.security.findings import FIX, INFORMATION, WATCH
from aistack.security.firewall import (
    HEADER,
    docker_filter,
    host_reach,
    parse_rule,
    parse_table,
    published_reach,
    read_firewall,
    reach,
)

NOW = datetime(2026, 11, 19, 19, 0, tzinfo=timezone.utc)

UFW = """\
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
:DOCKER-USER - [0:0]
:ufw-before-input - [0:0]
:ufw-user-input - [0:0]
-A INPUT -j ufw-before-input
-A FORWARD -j DOCKER-USER
-A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
-A DOCKER-USER -s 192.168.1.0/24 -i enp0s31f6 -j RETURN
-A DOCKER-USER -s 10.223.207.0/24 -i enp0s31f6 -j RETURN
-A DOCKER-USER -i enp0s31f6 -m limit --limit 6/min -j LOG --log-prefix "DOCKER-USER-REFUSE "
-A DOCKER-USER -i enp0s31f6 -j DROP
-A DOCKER-USER -j RETURN
-A ufw-before-input -i lo -j ACCEPT
-A ufw-before-input -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A ufw-before-input -p icmp -m icmp --icmp-type 3 -j ACCEPT
-A ufw-before-input -d 224.0.0.251/32 -p udp -m udp --dport 5353 -j ACCEPT
-A ufw-before-input -j ufw-user-input
-A ufw-user-input -s 192.168.1.0/24 -j ACCEPT
-A ufw-user-input -s 10.223.207.0/24 -j ACCEPT
-A ufw-user-input -s 192.168.1.40/32 -p tcp -m tcp --dport 3493 -j ACCEPT
COMMIT
"""

LAN = {"192.168.1.0/24", "10.223.207.0/24"}


def test_a_rule_is_read_with_its_source_ports_and_target() -> None:
    rule = parse_rule('-A ufw-user-input -s 10.0.0.0/8 -p tcp -m multiport --dports 80,443,8000:8010 -m comment --comment "web" -j ACCEPT')

    assert rule is not None
    assert (rule.source, rule.protocol, rule.target, rule.conditional) == ("10.0.0.0/8", "tcp", "ACCEPT", False)
    assert rule.dports == ((80, 80), (443, 443), (8000, 8010))


def test_a_rule_that_cannot_be_classified_is_conditional() -> None:
    for line in (
        "-A x -m conntrack --ctstate NEW -j ACCEPT",
        "-A x -d 224.0.0.251/32 -p udp -m udp --dport 5353 -j ACCEPT",
        "-A x ! -s 10.0.0.0/8 -j ACCEPT",
    ):
        rule = parse_rule(line)
        assert rule is not None and rule.conditional, line


def test_a_host_port_is_reached_from_the_networks_ufw_lets_in() -> None:
    table = parse_table(UFW)

    assert host_reach(table, "tcp", 22).origins == LAN
    assert host_reach(table, "tcp", 3493).origins == LAN | {"192.168.1.40/32"}
    assert host_reach(table, "udp", 5353).origins == LAN  # the multicast rule is set aside


def test_a_default_accept_or_an_open_rule_is_anywhere() -> None:
    assert host_reach(parse_table(":INPUT ACCEPT [0:0]\n"), "tcp", 22).anywhere

    opened = parse_table(UFW + "-A ufw-user-input -p tcp -m tcp --dport 22 -j ACCEPT\n")
    assert host_reach(opened, "tcp", 22).anywhere
    assert not host_reach(opened, "tcp", 80).anywhere


def test_an_interface_rule_is_open_to_that_interface() -> None:
    table = parse_table(":INPUT DROP [0:0]\n-A INPUT -i eth0 -p tcp -m tcp --dport 22 -j ACCEPT\n")

    found = host_reach(table, "tcp", 22)

    assert found.anywhere and found.origins == {"any on eth0"}


def test_a_jump_under_a_source_keeps_that_source() -> None:
    table = parse_table(
        ":INPUT DROP [0:0]\n-A INPUT -s 10.1.0.0/16 -j mine\n-A mine -p tcp -m tcp --dport 22 -j ACCEPT\n"
    )

    assert host_reach(table, "tcp", 22).origins == {"10.1.0.0/16"}


def test_docker_user_that_drops_the_rest_lets_in_only_what_returns() -> None:
    table = parse_table(UFW)

    assert docker_filter(table).iface == "enp0s31f6"
    assert published_reach(table).origins == LAN


def test_a_missing_or_open_docker_user_filters_nothing() -> None:
    assert published_reach(parse_table(":INPUT DROP [0:0]\n")).anywhere
    assert published_reach(parse_table(":DOCKER-USER - [0:0]\n-A DOCKER-USER -j RETURN\n")).anywhere


def _write(directory: Path, stamp: datetime, v4: str = UFW, v6: str | None = ":INPUT DROP [0:0]\n") -> None:
    (directory / "firewall-iptables.txt").write_text(f"{HEADER} {stamp.isoformat()}\n{v4}", encoding="utf-8")
    if v6 is not None:
        (directory / "firewall-ip6tables.txt").write_text(f"{HEADER} {stamp.isoformat()}\n{v6}", encoding="utf-8")


def test_the_snapshot_is_read_with_its_ipv6_side(tmp_path: Path) -> None:
    _write(tmp_path, NOW - timedelta(minutes=5))

    firewall, note = read_firewall(tmp_path, NOW)

    assert firewall is not None and note == "" and firewall.v6 is not None
    assert reach(firewall, "tcp", 22, False) == (host_reach(firewall.v4, "tcp", 22), True)


def test_ipv6_that_was_not_read_is_said(tmp_path: Path) -> None:
    _write(tmp_path, NOW, v6=None)

    firewall, _ = read_firewall(tmp_path, NOW)

    assert firewall is not None and reach(firewall, "tcp", 22, False)[1] is False


def test_no_snapshot_an_old_one_or_an_undated_one_is_not_judged(tmp_path: Path) -> None:
    assert read_firewall(tmp_path, NOW)[0] is None

    _write(tmp_path, NOW - timedelta(hours=3))
    firewall, note = read_firewall(tmp_path, NOW)
    assert firewall is None and "old" in note

    (tmp_path / "firewall-iptables.txt").write_text(UFW, encoding="utf-8")
    assert read_firewall(tmp_path, NOW)[0] is None


def _firewall(tmp_path: Path, v4: str = UFW):
    _write(tmp_path, NOW, v4)
    firewall, _ = read_firewall(tmp_path, NOW)
    assert firewall is not None
    return firewall


def test_a_sensitive_port_the_firewall_keeps_to_the_lan_is_information(tmp_path: Path) -> None:
    definition = SecurityDefinition(sensitive_ports={22: "SSH"})

    findings = assess([Listener("tcp", 22, ALL)], [], [], definition, _firewall(tmp_path))

    by_key = {finding.key: finding for finding in findings}
    assert by_key["exposure.sensitive.tcp.22"].severity == INFORMATION
    assert "10.223.207.0/24" in by_key["exposure.sensitive.tcp.22"].title
    assert "firewall.read" in by_key and "firewall.not_read" not in by_key


def test_a_sensitive_port_open_to_any_source_is_to_fix(tmp_path: Path) -> None:
    firewall = _firewall(tmp_path, UFW + "-A ufw-user-input -p tcp -m tcp --dport 22 -j ACCEPT\n")

    findings = assess([Listener("tcp", 22, ALL)], [], [], SecurityDefinition(sensitive_ports={22: "SSH"}), firewall)

    assert [finding.severity for finding in findings if finding.key == "exposure.sensitive.tcp.22"] == [FIX]


def test_a_critical_port_kept_to_the_lan_is_still_to_watch(tmp_path: Path) -> None:
    findings = assess([Listener("tcp", 2375, ALL)], [], [], SecurityDefinition(critical_ports={2375: "Docker API"}), _firewall(tmp_path))

    assert [finding.severity for finding in findings if finding.key == "exposure.critical.tcp.2375"] == [WATCH]


def test_a_published_port_is_judged_by_docker_user_not_by_input(tmp_path: Path) -> None:
    # INPUT accepts 8080 from anywhere, but the port is Docker's: DOCKER-USER decides.
    firewall = _firewall(tmp_path, UFW + "-A ufw-user-input -p tcp -m tcp --dport 8080 -j ACCEPT\n")

    findings = assess(
        [Listener("tcp", 8080, ALL)], [], [Published("web", "tcp", 8080, ALL)], SecurityDefinition(), firewall
    )

    assert "exposure.reachable_from_anywhere" not in {finding.key for finding in findings}


def test_an_undeclared_port_open_to_any_source_makes_one_finding(tmp_path: Path) -> None:
    firewall = _firewall(tmp_path, UFW + "-A ufw-user-input -p tcp -m tcp --dport 9000 -j ACCEPT\n")

    findings = assess([Listener("tcp", 9000, ALL), Listener("tcp", 9001, ALL)], [], [], SecurityDefinition(), firewall)

    opened = [finding for finding in findings if finding.key == "exposure.reachable_from_anywhere"]
    assert len(opened) == 1 and opened[0].evidence == ("9000/tcp",)


def test_without_a_snapshot_the_note_says_why() -> None:
    findings = assess([], [], [], SecurityDefinition(), None, "no firewall snapshot yet")

    not_read = next(finding for finding in findings if finding.key == "firewall.not_read")
    assert not_read.evidence == ("no firewall snapshot yet",)
