"""
What the assistant says itself, from real data, before any AI
(owner, 2026-10-09, UAT on GIGABYTE: "Faits d'abord, IA ensuite").

The first real use of the assistant on a backup gap (`nextcloud-files`,
État persistant) took 25 minutes and gave a recommendation with no
fact of the host in it: a 1.5 B model, on a Phenom II, given only the
finding's sentence, talked about energy savings and logs. A model of
this size cannot know the host; AIStack does. So the assistant states
first what it measured and what was declared (the finding's evidence,
and the declarations naming its subject), then what to do — the
domain's how-to, the finding's remediation, the block to write and
where, the command that shows it worked. The AI's opinion is asked
only afterwards, on the owner's click, and shown as an opinion.

Pure but for reading the declarations it is given.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from aistack.backup_strategy.yaml import load_backup_strategy_yaml
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.data_budget.budget import human_size
from aistack.pra.yaml import load_pra_tests_yaml
from aistack.priority.yaml import load_resource_priority_yaml

Translate = Callable[..., str]

CONSUMPTION = "Consommation CPU"
PRA_TESTS = "Tests PRA"
UNCOVERED_STATE = "État persistant"

# The cockpit's domain names → the plan's how-to (`plan.how_to.*`),
# the same text the action plan shows for the domain.
HOW_TO = {
    "Stockage": "storage",
    "Services": "services",
    "Sauvegarde / PRA": "backup",
    "GPU": "gpu",
    PRA_TESTS: "pra_tests",
    UNCOVERED_STATE: "uncovered_state",
    "Écarts d'inventaire": "inventory_gap",
    "Hôtes": "hosts",
    "Données d'AIStack": "data_budget",
}


@dataclass(frozen=True)
class Fact:
    label: str
    value: str


@dataclass(frozen=True)
class Guidance:
    facts: tuple[Fact, ...]
    steps: tuple[str, ...]
    # A block to write, and the file it goes into; empty when none.
    snippet: str = ""
    snippet_file: str = ""
    # A command that shows the fix worked; empty when none.
    verify: str = ""


@dataclass(frozen=True)
class Declarations:
    backup_strategy: Path
    pra_tests: Path
    resource_priority: Path


def _label(t: Translate, field: str) -> str:
    key = f"troubleshooting.fact.{field}"
    has = getattr(t, "has", None)
    return t(key) if has is not None and has(key) else field.replace("_", " ")


def _value(t: Translate, field: str, value: Any) -> str:
    if value is None and field in ("tested_at", "newest_file_mtime", "last_run"):
        return t("troubleshooting.fact.never")
    if value is None or value == "" or value == ():
        return t("troubleshooting.fact.none")
    if isinstance(value, bool):
        return t("troubleshooting.fact.answer_yes") if value else t("troubleshooting.fact.answer_no")
    if isinstance(value, int) and field.endswith("_bytes"):
        return human_size(value)
    if isinstance(value, float):
        return f"{value:.1f}"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return ", ".join(_value(t, field, item) for item in value)
    if dataclasses.is_dataclass(value):
        return str(getattr(value, "value", value))
    return str(value)


def evidence_facts(finding: RuntimeFinding, t: Translate) -> list[Fact]:
    """Every field of every reading the finding cites, as measured or declared."""

    facts: list[Fact] = []
    for cited in finding.evidence:
        reading = getattr(cited, "reading", None)
        if reading is None or not dataclasses.is_dataclass(reading):
            continue
        for field in dataclasses.fields(reading):
            facts.append(Fact(_label(t, field.name), _value(t, field.name, getattr(reading, field.name))))
    return facts


def _declared_backup(subject: str, path: Path, t: Translate) -> list[Fact]:
    try:
        definition = load_backup_strategy_yaml(path)
    except (OSError, ValueError):
        return []
    for service in definition:
        if service.service == subject:
            return [
                Fact(t("troubleshooting.fact.declared_engines"), _value(t, "engines", tuple(service.engines))),
                Fact(t("troubleshooting.fact.mechanism"), service.mechanism or t("troubleshooting.fact.none")),
            ]
    return [Fact(t("troubleshooting.fact.declared_engines"), t("troubleshooting.fact.not_declared"))]


def _declared_priority(subject: str, path: Path, t: Translate) -> list[Fact]:
    try:
        definition = load_resource_priority_yaml(path)
    except (OSError, ValueError):
        return []
    if any(app.container == subject for app in definition.priority):
        state = t("troubleshooting.fact.class_priority")
    elif any(container.name == subject for container in definition.background.containers):
        state = t("troubleshooting.fact.class_background")
    else:
        state = t("troubleshooting.fact.class_none")
    return [Fact(t("troubleshooting.fact.classification"), state)]


def _pra_max_age(subject: str, path: Path) -> int | None:
    try:
        _, register = load_pra_tests_yaml(path)
    except (OSError, ValueError):
        return None
    threshold = register.for_service(subject)
    return int(threshold.max_age_days) if threshold is not None else None


def _host(finding: RuntimeFinding) -> str:
    for cited in finding.evidence:
        host = getattr(getattr(cited, "reading", None), "host", "")
        if host:
            return str(host)
    return "<host>"


def guidance(
    domain: str,
    finding: RuntimeFinding,
    t: Translate,
    declarations: Declarations,
    remediation: str,
) -> Guidance:
    """What the assistant knows of this finding, and what to do."""

    subject = finding.subject
    facts = evidence_facts(finding, t)
    steps: list[str] = []
    how_to = HOW_TO.get(domain)
    if how_to is not None:
        steps.append(t(f"plan.how_to.{how_to}"))
    if remediation:
        steps.append(remediation)

    if domain == CONSUMPTION:
        facts += _declared_priority(subject, declarations.resource_priority, t)
        steps.append(t("troubleshooting.guide.consumption", subject=subject))
        return Guidance(
            tuple(facts),
            tuple(steps),
            verify=f"docker stats --no-stream {subject}",
        )

    if domain == PRA_TESTS:
        facts += _declared_backup(subject, declarations.backup_strategy, t)
        max_age = _pra_max_age(subject, declarations.pra_tests)
        if max_age is not None:
            facts.append(Fact(t("troubleshooting.fact.max_age_days"), str(max_age)))
        today = date.today().isoformat()
        return Guidance(
            tuple(facts),
            tuple(steps),
            snippet=(
                f"  - name: {subject}\n"
                "    last_test:\n"
                "      status: success\n"
                f'      date: "{today}"\n'
                "      rto_minutes: <minutes>\n"
            ),
            snippet_file="./config/pra_tests.yml",
            verify="python -m aistack.cli.health_render",
        )

    if domain == UNCOVERED_STATE:
        steps.append(t("troubleshooting.guide.uncovered_state", subject=subject))
        return Guidance(
            tuple(facts),
            tuple(steps),
            snippet=(
                f"  - name: {subject}\n"
                f"    host: {_host(finding)}\n"
                "    has_state: true\n"
                "    engines: [<dump_sql | stop_and_archive | live_file_backup>]\n"
                "    mechanism: >-\n"
                f"      <{t('troubleshooting.guide.mechanism_placeholder')}>\n"
            ),
            snippet_file="./config/backup_strategy.yml",
            verify="python -m aistack.cli.health_render",
        )

    return Guidance(tuple(facts), tuple(steps))
