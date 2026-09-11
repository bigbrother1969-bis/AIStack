"""
`evaluate` — the Kernel Runtime operation `claude/PLAN-TRAJECTOIRE
-2026-09-04.md` names J5: the first place two separately-collected
pieces of `aistack.kernel.evidence.Evidence` are correlated into a
qualified `RuntimeFinding` (STD-0300 § VS-4 criterion 4.5).

`ARCH-0008`/`CMP-0006` name `evaluate` as a Kernel Runtime operation
— "apply Knowledge Policies" — alongside `generate`/`render`, neither
of which is implemented as a `kernel.execution.task.Task` either;
this module is a plain function, the same shape `qualify`,
`correlate_findings` and `find_unexplained_consumption` already are
in this package, not a registered `Task`. `runtime_diagnose.py`'s own
pipeline calls all of those directly, never through the Kernel
Runtime's `Task`/`Request` machinery — `docker.discover` is that
machinery's only real subject to date, feeding a different pipeline
entirely. Building `evaluate` as a `Task` here would be infrastructure
this pipeline does not use anywhere else, not "sans réécrire ce qui
marche."

**What is correlated, and why only this pair.** The charter's own
example is `ContainerCpuReading` + `TemperatureReading`, and this
follows it exactly: `find_unexplained_consumption` (VS-4 4.1) already
names which containers are using CPU nobody declared an expectation
for — `OPS-0004`'s own definition of *energy inefficiency* almost
verbatim ("resource consumed for no functional benefit"). Whether
that consumption also carries the *sustainability anomaly* `OPS-0004`
distinguishes from it — "a physical consequence: heat generated, and
a risk to the hardware" — is exactly the correlation `OPS-0004` says
"nothing correlates... yet": a host temperature reading at or above
its own declared threshold, alongside that same consumption.

**Scoped to two of `OPS-0004`'s four qualifications, deliberately.**
*Technical debt* needs a corrections backlog no register in this
heritage tracks yet — `OPS-0004` itself declines to build one "until
a real pending correction exists to seed it with." *Deployment
misconfiguration* "keeps no definition at all" in `OPS-0004`, on
purpose, rather than one invented to fill a fourth slot. Citing
either here would be exactly the invention `GOV-P-001` forbids;
`evaluate` cites only what `OPS-0004` has actually defined and this
correlation actually evidences.

**Not a root-cause deriver.** STD-0300 § VS-4 criterion 4.6 needs a
second real, confirmed case before generalising one (`ARC-P-006`) —
this correlates two readings, it does not explain why either reads
what it does. A finding's `interpretation` states what was observed
correlated, not a derived cause.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.contracts.unexplained_consumption import UnexplainedConsumption

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS`
# (`aistack.contracts.runtime_finding`) for the full closed list this
# module's two citations are drawn from.
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"

# The `provider_id` each reading's source declares
# (`DockerProvider.provider_id`, `HostProvider.provider_id`) — a
# `CitedReading` names which one collected it, not what the finding
# means.
CPU_PROVIDER = "aistack.provider.docker"
HOST_PROVIDER = "aistack.provider.host"

# The signature `RuntimeFinding.signature` cites for every finding
# this module produces — `OPS-0004` itself, the register that
# authors the correlation applied here, the same role `OPS-0001/S-NNN`
# plays for a log-signature finding.
SIGNATURE = "OPS-0004"


def evaluate(
    consumption: Sequence[UnexplainedConsumption],
    temperatures: Sequence[TemperatureReading],
) -> tuple[RuntimeFinding, ...]:
    """
    Correlate unexplained CPU consumption against host temperature,
    into one qualified `RuntimeFinding` per container still carrying
    unexplained consumption.

    **One finding per `UnexplainedConsumption`, never per
    `TemperatureReading`.** A hot sensor with no unexplained
    consumption anywhere on the host is not, by itself, what this
    correlates — `OPS-0004` frames sustainability anomaly as a
    consequence *of* consumption, not a standalone reading; a finding
    here always states a container's own unexplained use first, and
    cites the host's temperature only as what that use may also carry.

    **A host reading with no declared threshold cites nothing.**
    `TemperatureReading.at_or_above_high`/`at_or_above_critical`
    return `None`, not `False`, when the sensor names no threshold —
    `bool(None)` is falsy, so an undeclared threshold correlates as
    "not shown to be hot" rather than as "not hot", the same
    "absent is not zero" reading `TemperatureReading`'s own docstring
    states.

    **Every hot reading collected is cited, not only the first.**
    `OPS-0004`'s own investigation named one sensor; a host reporting
    several hot at once is a stronger case for the same anomaly, not
    a choice between which one to believe.

    Pure: readings and consumption already collected in, findings
    out — the same discipline `find_unexplained_consumption` and
    `correlate_findings` already hold.
    """

    hot = tuple(
        reading
        for reading in temperatures
        if reading.at_or_above_high or reading.at_or_above_critical
    )

    findings = []

    for item in consumption:
        qualifications = [ENERGY_INEFFICIENCY]
        evidence: list[CitedReading] = [
            CitedReading(
                provider=CPU_PROVIDER,
                reading=ContainerCpuReading(
                    container=item.container,
                    cpu_percent=item.cpu_percent,
                ),
            )
        ]

        if hot:
            qualifications.append(SUSTAINABILITY_ANOMALY)
            evidence.extend(
                CitedReading(provider=HOST_PROVIDER, reading=reading)
                for reading in hot
            )

        findings.append(
            RuntimeFinding(
                subject=item.container,
                signature=SIGNATURE,
                interpretation=_interpretation(item, hot),
                remediation=_remediation(item, hot),
                confidence="Measured",
                grounding=UNDECLARED,
                evidence=tuple(evidence),
                qualifications=tuple(qualifications),
            )
        )

    return tuple(findings)


def _interpretation(
    item: UnexplainedConsumption, hot: tuple[TemperatureReading, ...]
) -> str:

    statement = (
        f"{item.container} used {item.cpu_percent:.1f}% CPU, at or "
        f"above the {item.threshold_percent:.1f}% threshold, with no "
        f"declared resource expectation in resource_priority.yml — "
        f"resource consumed for no declared functional benefit "
        f"({ENERGY_INEFFICIENCY})."
    )

    if not hot:
        return statement

    lead = hot[0]
    remainder = len(hot) - 1
    others = f" and {remainder} other sensor(s)" if remainder else ""

    return (
        f"{statement} The host also read {lead.celsius:.1f}°C on "
        f"{lead.sensor}{others}, at or above its own declared "
        f"threshold — a physical consequence correlated with the "
        f"same consumption ({SUSTAINABILITY_ANOMALY})."
    )


def _remediation(
    item: UnexplainedConsumption, hot: tuple[TemperatureReading, ...]
) -> str:

    statement = (
        f"Classify {item.container} in resource_priority.yml "
        f"(priority or background) so this consumption is either "
        f"expected or capped; investigate why it runs unexplained."
    )

    if not hot:
        return statement

    return (
        f"{statement} Check cooling and airflow before further "
        f"unclassified consumption adds to the heat "
        f"{hot[0].sensor} is already reporting."
    )
