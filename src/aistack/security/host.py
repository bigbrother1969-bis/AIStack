"""
The host's packages and sensitive files, read and judged (ADR-0028 § 2, slice T2c).

The assessment runs in a container that has no `apt` and cannot walk
`/root` or the other users' homes. A small root unit on the host
(`aistack-host-hygiene`) writes what `apt-get -s` plans and the rights
(mode, owner, group) of the files that hold secrets; this module reads
those files and judges them. It never reads a file's content, and a
finding names paths and numbers, never a secret.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import FIX, INFORMATION, WATCH, Finding

HEADER = "# aistack-collected-at:"
PACKAGES = "host-packages.txt"
FILES = "host-files.txt"
MAX_AGE = timedelta(hours=3)
# A host that reaches us by the push (ADR-0020) may be off for a day, and the
# push runs every 15 minutes: its snapshot is set aside after 25 hours, the
# threshold of `silent_after_minutes` in `hosts.yml`.
REMOTE_MAX_AGE = timedelta(hours=25)
REMOTE_DIRECTORY = "security"


@dataclass(frozen=True)
class Upgrade:
    name: str
    installed: str
    candidate: str
    security: bool


@dataclass(frozen=True)
class Packages:
    collected_at: datetime
    upgrades: tuple[Upgrade, ...]
    reboot_since: datetime | None
    lists_updated: datetime | None


@dataclass(frozen=True)
class SensitiveFile:
    mode: int
    owner: str
    group: str
    path: str


@dataclass(frozen=True)
class HostFiles:
    collected_at: datetime
    files: tuple[SensitiveFile, ...]


def _instant(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _collected_at(text: str) -> datetime | None:
    first = text.splitlines()[0] if text else ""
    return _instant(first[len(HEADER):]) if first.startswith(HEADER) else None


def parse_packages(text: str) -> Packages | None:
    collected = _collected_at(text)
    if collected is None:
        return None

    fields: dict[str, str] = {}
    upgrades: list[Upgrade] = []

    for line in text.splitlines()[1:]:
        key, _, value = line.partition(": ")
        if key == "package":
            parts = value.split()
            if len(parts) == 4:
                upgrades.append(Upgrade(parts[0], parts[1], parts[2], parts[3] == "security"))
        elif key:
            fields[key] = value

    return Packages(
        collected,
        tuple(upgrades),
        _instant(fields["reboot-required-since"]) if fields.get("reboot-required-since", "no") != "no" else None,
        _instant(fields["lists-updated"]) if fields.get("lists-updated", "unknown") != "unknown" else None,
    )


def parse_files(text: str) -> HostFiles | None:
    collected = _collected_at(text)
    if collected is None:
        return None

    files: list[SensitiveFile] = []

    for line in text.splitlines()[1:]:
        parts = line.split(maxsplit=3)
        if len(parts) != 4:
            continue
        try:
            mode = int(parts[0], 8)
        except ValueError:
            continue
        files.append(SensitiveFile(mode, parts[1], parts[2], parts[3]))

    return HostFiles(collected, tuple(files))


def read_host(directory: Path, now: datetime | None = None, max_age: timedelta = MAX_AGE) -> tuple[Packages | None, HostFiles | None, str]:
    """
    What the host unit wrote, and a sentence saying why a reading is missing
    or was set aside (empty when both are there and fresh).
    """

    now = now or datetime.now(timezone.utc)
    notes: list[str] = []

    def read(name: str, parse):
        try:
            text = (directory / name).read_text(encoding="utf-8")
        except OSError:
            return None
        reading = parse(text)
        if reading is None:
            notes.append(f"{name} has no date")
            return None
        if now - reading.collected_at > max_age:
            notes.append(f"{name} is old ({reading.collected_at.isoformat(timespec='minutes')})")
            return None
        return reading

    packages = read(PACKAGES, parse_packages)
    files = read(FILES, parse_files)

    if packages is None and files is None and not notes:
        return None, None, "no host snapshot yet: install the host unit aistack-host-hygiene"

    return packages, files, "; ".join(notes) + (": is the host unit still running?" if notes else "")


def _listed(names: list[str], limit: int) -> tuple[str, ...]:
    return tuple(names) if len(names) <= limit else (*names[:limit], f"and {len(names) - limit} more")


def _days(since: datetime, now: datetime) -> int:
    return max((now - since).days, 0)


def assess_packages(packages: Packages | None, note: str, now: datetime, definition: SecurityDefinition) -> list[Finding]:
    if packages is None:
        return [
            Finding(
                "host.packages.unread",
                INFORMATION,
                "The host's packages are not read from here",
                (note or "no package reading",),
                unknown="Whether upgrades, security ones included, are waiting on the host.",
            )
        ]

    findings: list[Finding] = []
    secure = [item for item in packages.upgrades if item.security]
    others = len(packages.upgrades) - len(secure)

    if secure:
        findings.append(
            Finding(
                "host.updates.security",
                WATCH,
                f"{len(secure)} security update(s) wait on the host",
                _listed([f"{item.name} {item.installed} -> {item.candidate}" for item in secure], definition.max_listed),
                unknown="How serious each one is for this host; only the package lists already on the disk are read.",
            )
        )

    if others:
        findings.append(
            Finding(
                "host.updates.pending",
                INFORMATION,
                f"{others} other update(s) wait on the host",
                unknown="What they change.",
            )
        )

    if packages.reboot_since is not None:
        days = _days(packages.reboot_since, now)
        findings.append(
            Finding(
                "host.reboot",
                WATCH if days > definition.max_reboot_pending_days else INFORMATION,
                f"A reboot is required since {days} day(s)",
                (f"since {packages.reboot_since.date().isoformat()}",),
                unknown="Which update needs it.",
            )
        )

    if packages.lists_updated is not None and _days(packages.lists_updated, now) > definition.max_apt_age_days:
        findings.append(
            Finding(
                "host.apt.stale",
                WATCH,
                f"The package lists were refreshed {_days(packages.lists_updated, now)} days ago",
                unknown="Whether newer updates exist; the lists are the base of every figure above.",
            )
        )

    return findings


def assess_files(files: HostFiles | None, definition: SecurityDefinition) -> list[Finding]:
    """Rights only: other access to a secret is a finding to fix, group access one to watch."""

    if files is None:
        return []

    accepted = set(definition.accepted_files)
    exposed = [item for item in files.files if item.mode & 0o007 and item.path not in accepted]
    shared = [item for item in files.files if not item.mode & 0o007 and item.mode & 0o070 and item.path not in accepted]
    taken = [item for item in files.files if item.path in accepted and item.mode & 0o077]

    def line(item: SensitiveFile) -> str:
        return f"{item.path}: {item.mode:04o} {item.owner}:{item.group}"

    findings: list[Finding] = []

    if exposed:
        findings.append(
            Finding(
                "host.files.exposed",
                FIX,
                f"{len(exposed)} sensitive file(s) can be reached by any user of the host",
                _listed([line(item) for item in exposed], definition.max_listed),
                unknown="Whether the content is a secret; only rights are read, never content.",
            )
        )

    if shared:
        findings.append(
            Finding(
                "host.files.group",
                WATCH,
                f"{len(shared)} sensitive file(s) can be reached by a group",
                _listed([line(item) for item in shared], definition.max_listed),
                unknown="Who is in the group; only rights are read, never content.",
            )
        )

    if taken:
        findings.append(
            Finding(
                "host.files.accepted",
                INFORMATION,
                f"{len(taken)} file(s) with wide rights are accepted in security.yml",
                _listed([item.path for item in taken], definition.max_listed),
                unknown="Whether each is still needed.",
            )
        )

    return findings


def read_remote_hosts(generated_dir: Path, now: datetime | None = None) -> list[tuple[str, Packages | None, HostFiles | None, str]]:
    """
    The snapshots of the other hosts: each host `hosts.yml` traces writes
    `<directory>/security/` through the push of `ADR-0020`. A host that has
    no such folder is not reported (it may not run the unit, and the local
    host is read from the folder of its own unit). An unreadable `hosts.yml`
    is no reason to fail the assessment.
    """

    from aistack.hosts.records import load_hosts_declaration

    try:
        hosts = load_hosts_declaration(generated_dir).hosts
    except (OSError, ValueError, AttributeError):
        return []

    found = []
    for host in hosts:
        folder = host.directory / REMOTE_DIRECTORY
        if folder.is_dir():
            found.append((host.name, *read_host(folder, now, REMOTE_MAX_AGE)))
    return found


def assess_remote_hosts(
    hosts: list[tuple[str, Packages | None, HostFiles | None, str]],
    now: datetime,
    definition: SecurityDefinition,
) -> list[Finding]:
    """The same judgement as the local host, each finding naming its host."""

    findings: list[Finding] = []
    for name, packages, files, note in hosts:
        for finding in assess_packages(packages, note, now, definition) + assess_files(files, definition):
            findings.append(
                replace(finding, key=finding.key.replace("host.", f"host.{name}.", 1), title=f"{name}: {finding.title}")
            )
    return findings
