"""
The firewall's rules, read and judged (ADR-0028 § 2, slice T1b).

The assessment runs in a container without `iptables`, and a reading made
from a private network namespace would say "no rule" about a host that has
some. A small root unit on the host (`aistack-firewall-snapshot`) writes
what `iptables-save` and `ip6tables-save` say; this module reads those
files and answers one question per port: **from where can it be reached?**

It reads the rules ufw writes (`INPUT` and the chains it jumps to) and the
`DOCKER-USER` chain. It is an approximation, and says so: a rule it cannot
classify (a connection-state match, a destination address, a source port)
is set aside, never counted as an opening. It reports what the firewall
lets in, not what a router in front of it forwards.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEADER = "# aistack-collected-at:"
MAX_AGE = timedelta(hours=2)
ANYWHERE = "anywhere"

_TERMINAL = {"ACCEPT", "DROP", "REJECT", "RETURN", "LOG", "QUEUE", "NFQUEUE"}
# Modules that only name a protocol, ports or a comment; any other module
# makes a rule conditional (connection state, addresses, limits).
_PLAIN_MODULES = {"tcp", "udp", "multiport", "comment"}


@dataclass(frozen=True)
class Rule:
    chain: str
    target: str
    source: str | None = None
    in_iface: str | None = None
    protocol: str | None = None
    dports: tuple[tuple[int, int], ...] | None = None
    conditional: bool = False


@dataclass
class Table:
    """One `iptables-save` reading: the chains' default policies and their rules."""

    policies: dict[str, str] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)

    def chain(self, name: str) -> list[Rule]:
        return [rule for rule in self.rules if rule.chain == name]

    def has_chain(self, name: str) -> bool:
        return name in self.policies or any(rule.chain == name for rule in self.rules)


@dataclass(frozen=True)
class Firewall:
    collected_at: datetime
    v4: Table
    v6: Table | None


@dataclass(frozen=True)
class Reach:
    """From where a port can be reached: origins named, or `anywhere`."""

    origins: frozenset[str]

    @property
    def anywhere(self) -> bool:
        return ANYWHERE in self.origins or any(item.startswith("any on ") for item in self.origins)

    def text(self) -> str:
        return ", ".join(sorted(self.origins)) if self.origins else "nothing"


def _ports(value: str) -> tuple[tuple[int, int], ...] | None:
    spans: list[tuple[int, int]] = []
    for part in value.split(","):
        low, _, high = part.partition(":")
        try:
            spans.append((int(low), int(high or low)))
        except ValueError:
            return None
    return tuple(spans)


def parse_rule(line: str) -> Rule | None:
    try:
        tokens = shlex.split(line)
    except ValueError:
        return None

    if len(tokens) < 2 or tokens[0] != "-A":
        return None

    chain = tokens[1]
    fields: dict[str, str] = {}
    modules: set[str] = set()
    conditional = False
    index = 2

    while index < len(tokens):
        token = tokens[index]
        value = tokens[index + 1] if index + 1 < len(tokens) else ""

        if token == "!":
            conditional = True
            index += 1
            continue

        if token in {"-s", "-i", "-p", "-d", "-o", "-j", "-g", "--dport", "--dports", "--sport", "--sports", "-m"}:
            if token == "-m":
                modules.add(value)
            else:
                fields[token] = value
            index += 2
            continue

        # `--comment "..."`, `--ctstate X`, `--limit X`: an option and its value.
        index += 2 if token.startswith("-") and value and not value.startswith("-") else 1

    if modules - _PLAIN_MODULES or {"-d", "-o", "--sport", "--sports"} & fields.keys():
        conditional = True

    port_text = fields.get("--dport") or fields.get("--dports")
    dports = _ports(port_text) if port_text else None

    if port_text and dports is None:
        conditional = True

    return Rule(
        chain=chain,
        target=fields.get("-j") or fields.get("-g") or "",
        source=fields.get("-s"),
        in_iface=fields.get("-i"),
        protocol=fields.get("-p"),
        dports=dports,
        conditional=conditional,
    )


def parse_table(text: str) -> Table:
    table = Table()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(":"):
            name, _, rest = line[1:].partition(" ")
            table.policies[name] = rest.split(" ", 1)[0]
        elif line.startswith("-A "):
            rule = parse_rule(line)
            if rule is not None:
                table.rules.append(rule)
    return table


def _matches(rule: Rule, protocol: str, port: int) -> bool:
    if rule.protocol not in (None, "all", protocol):
        return False
    if rule.dports is None:
        return True
    return any(low <= port <= high for low, high in rule.dports)


def _origin(source: str | None, iface: str | None) -> str:
    if source and source not in {"0.0.0.0/0", "::/0"}:
        return source
    return f"any on {iface}" if iface else ANYWHERE


def _accepted(table: Table, chain: str, protocol: str, port: int, inherited: tuple[str | None, str | None], seen: set[str]) -> set[str]:
    if chain in seen:
        return set()
    seen = seen | {chain}
    origins: set[str] = set()

    for rule in table.chain(chain):
        if rule.conditional or not _matches(rule, protocol, port) or rule.in_iface == "lo":
            continue

        source = rule.source or inherited[0]
        iface = rule.in_iface or inherited[1]

        if rule.target == "ACCEPT":
            origins.add(_origin(source, iface))
        elif rule.target not in _TERMINAL and table.has_chain(rule.target):
            origins |= _accepted(table, rule.target, protocol, port, (source, iface), seen)

    return origins


def host_reach(table: Table, protocol: str, port: int) -> Reach:
    """From where `protocol/port` of the host itself can be reached (the INPUT chain)."""

    if table.policies.get("INPUT") == "ACCEPT":
        return Reach(frozenset({ANYWHERE}))
    return Reach(frozenset(_accepted(table, "INPUT", protocol, port, (None, None), set())))


@dataclass(frozen=True)
class DockerFilter:
    """What DOCKER-USER does to the traffic bound for a published port."""

    drops: bool
    iface: str | None
    allowed: tuple[str, ...]


def docker_filter(table: Table) -> DockerFilter:
    rules = [rule for rule in table.chain("DOCKER-USER") if not rule.conditional]
    drop = next(
        (
            rule
            for rule in rules
            if rule.target in {"DROP", "REJECT"} and rule.source is None and rule.dports is None and rule.protocol in (None, "all")
        ),
        None,
    )

    if drop is None:
        return DockerFilter(False, None, ())

    allowed = tuple(
        sorted(
            {
                rule.source
                for rule in rules
                if rule.target in {"RETURN", "ACCEPT"} and rule.source and rule.in_iface in (None, drop.in_iface)
            }
        )
    )
    return DockerFilter(True, drop.in_iface, allowed)


def published_reach(table: Table) -> Reach:
    docker = docker_filter(table)
    if not docker.drops:
        return Reach(frozenset({ANYWHERE}))
    return Reach(frozenset(docker.allowed))


def reach(firewall: Firewall, protocol: str, port: int, published: bool) -> tuple[Reach, bool]:
    """
    From where a port can be reached, over IPv4 and IPv6 together, and
    whether the IPv6 side could be read at all.
    """

    tables = [firewall.v4] + ([firewall.v6] if firewall.v6 is not None else [])
    origins: set[str] = set()

    for table in tables:
        # IPv6 without a DOCKER-USER chain: Docker does not forward it, and
        # what answers is the userland proxy, a host socket the INPUT chain guards.
        filtered = published and (table is firewall.v4 or table.has_chain("DOCKER-USER"))
        found = published_reach(table) if filtered else host_reach(table, protocol, port)
        origins |= found.origins

    return Reach(frozenset(origins)), firewall.v6 is not None


def read_firewall(directory: Path, now: datetime | None = None) -> tuple[Firewall | None, str]:
    """
    The snapshot the host unit wrote, and a sentence saying why there is
    none or why it was set aside. IPv6 is optional; IPv4 is required.
    """

    now = now or datetime.now(timezone.utc)
    v4_path = directory / "firewall-iptables.txt"
    v6_path = directory / "firewall-ip6tables.txt"

    try:
        v4_text = v4_path.read_text(encoding="utf-8")
    except OSError:
        return None, "no firewall snapshot yet: install the host unit aistack-firewall-snapshot"

    collected = _collected_at(v4_text)
    if collected is None:
        return None, "the firewall snapshot has no date"

    if now - collected > MAX_AGE:
        return None, f"the firewall snapshot is old ({collected.isoformat(timespec='minutes')}): is the host unit still running?"

    try:
        v6 = parse_table(v6_path.read_text(encoding="utf-8"))
    except OSError:
        v6 = None

    return Firewall(collected, parse_table(v4_text), v6), ""


def _collected_at(text: str) -> datetime | None:
    first = text.splitlines()[0] if text else ""
    if not first.startswith(HEADER):
        return None
    try:
        value = datetime.fromisoformat(first[len(HEADER):].strip())
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
