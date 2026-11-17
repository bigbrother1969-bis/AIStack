"""
The findings the Troubleshooting Assistant can guide someone through
(`ADR-0012` § 4), collected fresh from the host on each request.

Covers the CPU consumption check plus every Cockpit Santé domain, built
by `aistack.health.domains` — the one place that builds the cockpit
(`GOV-0002/OS-093`). Only a consumption finding can be applied
(`aistack.troubleshooting.apply`).
"""

from __future__ import annotations

import socket
import subprocess
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NamedTuple

from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.health import domains
from aistack.health.domains import build_cockpit
from aistack.kernel.bootstrap import registered_providers
from aistack.kernel.registries import ProviderRegistry
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.providers.docker import DockerProvider
from aistack.providers.host.provider import HostProvider
from aistack.runtime.evaluate import evaluate
from aistack.runtime.idle_consumption import find_unexplained_consumption


def resource_priority_definition(
    path: Path,
) -> tuple[ResourcePriorityDefinition | None, str]:
    """Mirrors `aistack.cli.ai_reason.resource_priority_definition` exactly."""

    if not path.exists():
        return None, (
            f"no resource-priority definition at {path}; consumption "
            f"is not checked"
        )

    try:
        return load_resource_priority_yaml(path), ""
    except (ValueError, OSError) as error:
        return None, (
            f"resource-priority definition not readable ({error}); "
            f"consumption is not checked"
        )


def _consumption_findings(
    providers: ProviderRegistry | None = None,
) -> tuple[tuple[RuntimeFinding, ...], str]:
    """
    The CPU/temperature findings of `aistack.runtime.evaluate`, freshly
    collected, as in `aistack.cli.ai_reason.qualified_findings`.
    """

    definition, note = resource_priority_definition(domains.SOURCES.resource_priority)

    if definition is None:
        return (), note

    try:
        readings = registered_providers(providers).get_as("docker", DockerProvider).collect_cpu_readings()
    except (subprocess.SubprocessError, OSError) as error:
        return (), (
            f"CPU readings could not be collected ({error}); "
            f"nothing to reason about"
        )

    consumption = find_unexplained_consumption(readings, definition)
    temperatures = registered_providers(providers).get_as("host", HostProvider).collect_temperatures()

    return evaluate(consumption, temperatures), ""


# The domain builders below mirror `aistack.cli.health_render`, where each
# domain is documented.


# Label for the CPU consumption findings, which come from no cockpit domain.
CONSUMPTION_DOMAIN = "Consommation CPU"

# Only consumption findings may be applied (`/finding/{key}/apply`).
APPLYABLE_DOMAINS = frozenset({CONSUMPTION_DOMAIN})


class QualifiedFinding(NamedTuple):
    """
    One finding with its domain and routing key.

    Two domains can flag the same subject (e.g. a service in both Tests PRA
    and État persistant), so routing on the subject alone would hide one of
    them. `key` is the subject when unique in the set, else
    `"<domain>::<subject>"`. `finding.subject` itself is never changed.
    """

    key: str
    domain: str
    finding: RuntimeFinding

    @property
    def applyable(self) -> bool:
        return self.domain in APPLYABLE_DOMAINS


def qualified_findings(
    providers: ProviderRegistry | None = None,
) -> tuple[tuple[QualifiedFinding, ...], str]:
    """
    Every finding the assistant can guide someone through: the CPU
    consumption check plus every domain of `build_cockpit`, each tagged
    with its domain. Uninstrumented domains contribute nothing.

    `note` is set only when the consumption check could not run at all.
    """

    # One Kernel for the consumption check and the whole cockpit: the one
    # given (the web application's own), else one booted for the occasion.
    providers = registered_providers(providers)

    consumption_findings, note = _consumption_findings(providers)
    cockpit = build_cockpit(socket.gethostname(), providers)

    tagged: list[tuple[str, RuntimeFinding]] = [
        (CONSUMPTION_DOMAIN, finding) for finding in consumption_findings
    ]
    for domain in cockpit.domains:
        tagged.extend((domain.name, finding) for finding in domain.findings)

    return qualify(tagged), note


def qualify(tagged: Iterable[tuple[str, RuntimeFinding]]) -> tuple[QualifiedFinding, ...]:
    """
    Give each (domain, finding) its routing key: the bare subject when
    no other finding in the set shares it, `"<domain>::<subject>"` when
    one does (`QualifiedFinding` says why).
    """

    pairs = list(tagged)
    subject_counts: dict[str, int] = {}

    for _, finding in pairs:
        subject_counts[finding.subject] = subject_counts.get(finding.subject, 0) + 1

    return tuple(
        QualifiedFinding(
            key=(
                finding.subject
                if subject_counts[finding.subject] == 1
                else f"{domain_name}::{finding.subject}"
            ),
            domain=domain_name,
            finding=finding,
        )
        for domain_name, finding in pairs
    )


CollectFindings = Callable[[], "tuple[tuple[QualifiedFinding, ...], str]"]
