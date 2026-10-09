"""
The "Données d'AIStack" domain of the health cockpit (`ADR-0021`): one
finding when AIStack's data passes `warn_percent` of its budget, a more
pressing one past the budget itself. Written once for the three places
that build the cockpit.
"""

from __future__ import annotations

from pathlib import Path

from aistack.contracts.data_usage import DataUsageReading
from aistack.contracts.finding_message import FindingMessage, part
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED
from aistack.data_budget.budget import human_size, load_data_budget, measure
from aistack.health.cockpit import HealthDomain

DOMAIN = "Données d'AIStack"
SIGNATURE = "ADR-0021"
SOURCE = "aistack.data_budget.budget.measure"
QUALIFICATIONS = ("OPS-0004/sustainability-anomaly",)
GENERATED_DIR = Path("reports/generated")
OVER = "findings.data_budget.over.interpretation"
NEAR = "findings.data_budget.near.interpretation"


def evaluate_data_usage(reading: DataUsageReading) -> tuple[RuntimeFinding, ...]:
    if reading.percent < reading.warn_percent:
        return ()
    over = reading.used_bytes >= reading.budget_bytes
    used, budget = human_size(reading.used_bytes), human_size(reading.budget_bytes)
    days = reading.days_left
    if over:
        interpretation = (
            f"AIStack's data takes {used}, past its budget of {budget} "
            f"({reading.percent} %) (ADR-0021)."
        )
        message = part(OVER, used=used, budget=budget, percent=reading.percent)
    else:
        interpretation = (
            f"AIStack's data takes {used}, {reading.percent} % of its budget "
            f"of {budget}; the budget is reached in about "
            f"{days if days is not None else '?'} day(s) at the pace of the "
            f"last seven (ADR-0021)."
        )
        message = part(
            NEAR,
            used=used,
            budget=budget,
            percent=reading.percent,
            days=days if days is not None else "?",
        )
    biggest = ", ".join(f"{name} {human_size(size)}" for name, size in reading.largest[:3])
    remediation = (
        f"Largest: {biggest}. Compress older observations "
        f"(python -m aistack.cli.data_budget --compress), shorten "
        f"compress_after_days, or raise budget_mb in ./config/data_budget.yml."
    )
    return (
        RuntimeFinding(
            subject=reading.directory,
            signature=SIGNATURE,
            interpretation=interpretation,
            remediation=remediation,
            message=FindingMessage(
                interpretation=(message,),
                remediation=(part("findings.data_budget.remediation", biggest=biggest),),
            ),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(CitedReading(provider=SOURCE, reading=reading),),
            qualifications=QUALIFICATIONS,
        ),
    )


def data_budget_domain(generated_dir: Path = GENERATED_DIR) -> HealthDomain:
    try:
        budget = load_data_budget()
    except (OSError, ValueError) as error:
        return HealthDomain(
            name=DOMAIN,
            instrumented=False,
            note=f"data budget not readable ({error}); AIStack's own data is not checked",
        )
    if not generated_dir.is_dir():
        return HealthDomain(
            name=DOMAIN,
            instrumented=False,
            note=f"no data directory at {generated_dir}; AIStack's own data is not checked",
        )
    return HealthDomain(
        name=DOMAIN, instrumented=True, findings=evaluate_data_usage(measure(generated_dir, budget))
    )
