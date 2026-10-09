"""
The Hosts domain of the health cockpit (2.0; the owner, 2026-10-09:
"hôte silencieux = constat Santé").

`ADR-0020` traces what changes on each host through a collector run
every 15 minutes. A collector that stops writing — its timer disabled,
the host down, the Raspberry's disk not mounted — leaves a gap in the
record that nothing used to say outside `python -m aistack.cli.hosts`.
Here each traced host with no run for longer than `hosts.yml`'s
`silent_after_minutes` becomes a finding, on the cockpit, in the score
and in the troubleshooting assistant.

One module for the three places that build the cockpit
(`aistack.cli.health_render`, `aistack.cli.console_render`,
`aistack.troubleshooting.findings`), so the domain is written once.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

from aistack.contracts.finding_message import FindingMessage, part
from aistack.contracts.host_silence import HostSilence
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED
from aistack.health.cockpit import HealthDomain
from aistack.hosts.records import HostRecords, load_hosts_declaration, now_utc, read_all

DOMAIN = "Hôtes"
SIGNATURE = "ADR-0020"
SOURCE = "aistack.hosts.records.read_host"
# A collector that stopped writing is a deployment that no longer does
# what it was installed for; it is not debt, nor a waste of energy.
QUALIFICATIONS = ("OPS-0004/deployment-misconfiguration",)
GENERATED_DIR = Path("reports/generated")


def find_silent_hosts(
    records: Sequence[HostRecords], now: datetime, after_minutes: float
) -> tuple[HostSilence, ...]:
    """Every host with no run read, or none for longer than `after_minutes`."""

    found = []
    for host in records:
        last = host.last_run
        if last is None:
            found.append(
                HostSilence(
                    host.host,
                    str(host.directory),
                    problem=host.problem or f"no last run in {host.directory}/host.json",
                )
            )
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=now.tzinfo)
        minutes = int((now - last).total_seconds() // 60)
        if minutes > after_minutes:
            found.append(HostSilence(host.host, str(host.directory), last.isoformat(timespec="minutes"), minutes))
    return tuple(found)


def evaluate_silent_hosts(silences: Sequence[HostSilence]) -> tuple[RuntimeFinding, ...]:
    return tuple(
        RuntimeFinding(
            subject=silence.host,
            signature=SIGNATURE,
            interpretation=_interpretation(silence),
            remediation=_remediation(silence),
            message=_message(silence),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(CitedReading(provider=SOURCE, reading=silence),),
            qualifications=QUALIFICATIONS,
        )
        for silence in silences
    )


def _interpretation(silence: HostSilence) -> str:
    if silence.minutes is None:
        return (
            f"No record from the collector of host {silence.host} in "
            f"{silence.directory} ({silence.problem}): what changes on this "
            f"host is not traced (ADR-0020)."
        )
    return (
        f"The collector of host {silence.host} has written nothing for "
        f"{silence.minutes} minutes (last run: {silence.last_run}): what "
        f"changes on this host is no longer traced (ADR-0020)."
    )


def _remediation(silence: HostSilence) -> str:
    return (
        f"On {silence.host}: systemctl status aistack-host-collector.timer "
        f"and journalctl -u aistack-host-collector; for a host writing to "
        f"a shared disk, also check the disk is mounted on both sides "
        f"(manual, \"Traceability of the hosts\")."
    )


def _message(silence: HostSilence) -> FindingMessage:
    if silence.minutes is None:
        interpretation = part(
            "findings.host_silence.no_record.interpretation",
            host=silence.host,
            directory=silence.directory,
            problem=silence.problem,
        )
    else:
        interpretation = part(
            "findings.host_silence.silent.interpretation",
            host=silence.host,
            minutes=silence.minutes,
            last_run=silence.last_run,
        )
    return FindingMessage(
        interpretation=(interpretation,),
        remediation=(part("findings.host_silence.remediation", host=silence.host),),
    )


def hosts_domain(
    generated_dir: Path = GENERATED_DIR,
    now: datetime | None = None,
    declaration: Path | None = None,
) -> HealthDomain:
    """The Hosts domain; not instrumented when `hosts.yml` cannot be read."""

    try:
        hosts = load_hosts_declaration(generated_dir, declaration)
    except (OSError, ValueError) as error:
        return HealthDomain(
            name=DOMAIN,
            instrumented=False,
            note=f"host declaration not readable ({error}); host collectors are not checked",
        )
    if not hosts.hosts:
        return HealthDomain(
            name=DOMAIN,
            instrumented=False,
            note="hosts.yml traces no host; host collectors are not checked",
        )
    silences = find_silent_hosts(
        read_all(hosts), now or now_utc(), hosts.silent_after.total_seconds() / 60
    )
    return HealthDomain(name=DOMAIN, instrumented=True, findings=evaluate_silent_hosts(silences))
