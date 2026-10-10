"""
Correlate unexplained CPU consumption with host temperature into qualified
`RuntimeFinding`s.

Each container with undeclared CPU use is qualified as energy inefficiency;
if any host sensor reads at or above its declared threshold, the finding is
also qualified as a sustainability anomaly. When the container's logs are
available, whether they show incoming HTTP requests is added to the
interpretation only, never to the qualifications. A finding states what was
observed together, not a root cause.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Mapping, Sequence

from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.runtime_observation import RuntimeObservation
from aistack.contracts.temperature_reading import TemperatureReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.runtime.activity_evidence import no_incoming_requests

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"

# The `provider_id` of the provider that collected each cited reading.
CPU_PROVIDER = "aistack.provider.docker"
HOST_PROVIDER = "aistack.provider.host"

SIGNATURE = "OPS-0004"


def evaluate(
    consumption: Sequence[UnexplainedConsumption],
    temperatures: Sequence[TemperatureReading],
    observations: Mapping[str, RuntimeObservation] | None = None,
) -> tuple[RuntimeFinding, ...]:
    """
    Return one `RuntimeFinding` per `UnexplainedConsumption`, never per
    temperature reading: heat is cited only as a consequence of consumption.

    `observations` maps a container to its log observation; a container
    missing from it gets no statement about requests either way. A sensor
    with no declared threshold reads as "not shown to be hot", not "not hot".
    Every hot reading is cited, not only the first.
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
                message=_message(item, hot, quiet),
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
            "work remain unchecked."
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


def _message(
    item: UnexplainedConsumption,
    hot: tuple[TemperatureReading, ...],
    quiet: bool | None,
) -> FindingMessage:
    """
    The same two sentences as `_interpretation`/`_remediation`, as
    catalog keys — a statement, then each clause the readings add.
    """

    interpretation = [
        part(
            "findings.consumption.statement.interpretation",
            container=item.container,
            cpu=f"{item.cpu_percent:.1f}",
            threshold=f"{item.threshold_percent:.1f}",
            qualification=ENERGY_INEFFICIENCY,
        )
    ]

    if quiet is True:
        interpretation.append(part("findings.consumption.quiet.interpretation"))
    elif quiet is False:
        interpretation.append(part("findings.consumption.busy.interpretation"))

    remediation = [part("findings.consumption.statement.remediation", container=item.container)]

    if hot:
        lead = hot[0]
        remainder = len(hot) - 1
        values = dict(
            celsius=f"{lead.celsius:.1f}",
            sensor=lead.sensor,
            qualification=SUSTAINABILITY_ANOMALY,
        )
        interpretation.append(
            part("findings.consumption.hot_others.interpretation", others=remainder, **values)
            if remainder
            else part("findings.consumption.hot.interpretation", **values)
        )
        remediation.append(part("findings.consumption.hot.remediation", sensor=lead.sensor))

    return FindingMessage(interpretation=tuple(interpretation), remediation=tuple(remediation))
