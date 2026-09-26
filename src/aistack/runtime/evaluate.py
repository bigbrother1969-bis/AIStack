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
misconfiguration* was undefined when this was written, 2026-09-11;
`OPS-0004`'s second reference incident has since named it (GIGABYTE
disk exhaustion), and `aistack.runtime.evaluate_storage` — not this
function — is what cites it, from a `StorageShortage`, not from
`ContainerCpuReading`/`TemperatureReading`. This function still cites
only what it actually correlates: adding a citation here without a
storage reading to back it would be exactly the invention `GOV-P-001`
forbids.

**Not a root-cause deriver.** STD-0300 § VS-4 criterion 4.6 needs a
second real, confirmed case before generalising one (`ARC-P-006`) —
this correlates two readings, it does not explain why either reads
what it does. A finding's `interpretation` states what was observed
correlated, not a derived cause.

**A third, optional correlation, added 2026-09-26: `observations`.**
STD-0300 § VS-4 criterion 4.1 asks for *idle* consumption, and
`find_unexplained_consumption` only ever established "elevated and
undeclared" — nothing distinguished that from a container nobody has
classified but which is, in fact, doing real work. `aistack.runtime
.activity_evidence.no_incoming_requests` is real, tested evidence
built for this exact reading (`OPS-0004`'s own reference incident
lists "no incoming HTTP requests" among what made `aistack
-selection-ui`'s consumption idle rather than legitimate), collected
in the same run `qualify()` already reads a container's logs in —
this only stops leaving it uncalled. It is folded into
`interpretation`, never into `qualifications`: what counts as
*energy inefficiency* is `OPS-0004`'s own vocabulary, and narrowing
or widening it based on one more signal would be exactly the
invention `GOV-P-001` forbids — this states what the logs also
showed, and lets a reader judge it alongside the rest.

**What this still does not prove.** `no_incoming_requests`'s own
docstring is explicit: a quiet window is not proof nothing arrived,
and it says nothing about an active browser session — the other half
of the reference incident's own evidence, which nothing here checks.
A container with no request seen is stated as exactly that, not as
"confirmed idle"; a container `observations` carries no entry for is
stated as neither — the same "absent is not a negative answer"
`TemperatureReading`'s own threshold reading already holds.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.runtime_observation import RuntimeObservation
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.runtime.activity_evidence import no_incoming_requests

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
    observations: Mapping[str, RuntimeObservation] | None = None,
) -> tuple[RuntimeFinding, ...]:
    """
    Correlate unexplained CPU consumption against host temperature,
    into one qualified `RuntimeFinding` per container still carrying
    unexplained consumption.

    `observations` is `container -> RuntimeObservation`, optional and
    `None` by default so every existing caller and test built before
    2026-09-26 is unaffected — a container absent from it, or the
    argument left out entirely, is read exactly like a sensor with no
    declared threshold: not shown either way, never assumed quiet.

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

    observed = observations or {}

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

        observation = observed.get(item.container)
        quiet = no_incoming_requests(observation) if observation else None

        findings.append(
            RuntimeFinding(
                subject=item.container,
                signature=SIGNATURE,
                interpretation=_interpretation(item, hot, quiet),
                remediation=_remediation(item, hot),
                confidence="Measured",
                grounding=UNDECLARED,
                evidence=tuple(evidence),
                qualifications=tuple(qualifications),
            )
        )

    return tuple(findings)


def _interpretation(
    item: UnexplainedConsumption,
    hot: tuple[TemperatureReading, ...],
    quiet: bool | None,
) -> str:

    statement = (
        f"{item.container} used {item.cpu_percent:.1f}% CPU, at or "
        f"above the {item.threshold_percent:.1f}% threshold, with no "
        f"declared resource expectation in resource_priority.yml — "
        f"resource consumed for no declared functional benefit "
        f"({ENERGY_INEFFICIENCY})."
    )

    if quiet is True:
        statement += (
            " Its own logs, read in the same run, show no incoming "
            "HTTP requests — consistent with resource used at rest, "
            "though an active session and every non-HTTP shape of "
            "work remain unchecked (STD-0300 § VS-4 criterion 4.1)."
        )
    elif quiet is False:
        statement += (
            " Its own logs, read in the same run, do show incoming "
            "HTTP requests in this window — this consumption may "
            "reflect real work rather than idling; classification in "
            "resource_priority.yml is still what is missing."
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
