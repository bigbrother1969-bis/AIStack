from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aistack.contracts.correlated_finding import CorrelatedFinding
from aistack.contracts.development_flag import DevelopmentFlagFinding
from aistack.contracts.lifecycle import LifecycleRegister
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.signature import SignatureCatalogue
from aistack.contracts.unexplained_consumption import UnexplainedConsumption
from aistack.policies.lifecycle_register import (
    RegisterError,
    read_lifecycle_register,
)
from aistack.policies.signature_catalogue import (
    CatalogueError,
    read_signature_catalogue,
)
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.providers.docker import DockerProvider
from aistack.runtime.correlation import correlate_findings
from aistack.runtime.deployment_definition import extract_dockerfile_command
from aistack.runtime.development_flags import find_development_flags
from aistack.runtime.grounding import ground_findings
from aistack.runtime.idle_consumption import find_unexplained_consumption
from aistack.runtime.qualification import qualify


# The governed catalogue, relative to the repository root.
#
# ADR-0009 § 2 made `docs/` an input to execution, and this is
# where that lands in practice: the path is resolved from this
# module's location, four levels up, which holds while AIStack is
# run from its source tree.
#
# An installed distribution does not ship `docs/`. The wheel
# contains `aistack/` and nothing else, so a packaged AIStack
# cannot find this file and must be given `--catalogue`. That
# consequence is recorded in GOV-0002 rather than worked around
# here.
DEFAULT_CATALOGUE = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "04-development"
    / "OPS-0001-Container-Log-Signatures.md"
)


# The governed lifecycle register, next to the catalogue for the
# same reason and with the same consequence for a packaged install.
#
# **Optional, unlike the catalogue.** A finding is qualified against
# `OPS-0001` or it does not exist; grounding it against `OPS-0003`
# only adds owner context where one has been declared. A missing or
# unreadable register is reported and the run continues with no
# declarations, rather than refusing to diagnose because an
# enrichment step could not enrich anything.
DEFAULT_LIFECYCLE_REGISTER = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "04-development"
    / "OPS-0003-Container-Lifecycle-Declarations.md"
)


def lifecycle_register(path: Path) -> tuple[LifecycleRegister, str]:
    """
    Read the lifecycle register at `path`, or an empty one with a
    note explaining why.

    Returns the register and a note for the report — never raises.
    `STD-0300` § VS-4 criterion 4.7 is advanced by this register
    where one is declared; a host with none yet, or a packaged
    install carrying no `docs/`, still diagnoses, just without that
    context.
    """

    if not path.exists():
        return LifecycleRegister(artifact="none"), (
            f"no lifecycle register at {path}; findings are not "
            f"grounded against one"
        )

    try:
        return read_lifecycle_register(path.read_text(encoding="utf-8")), ""
    except RegisterError as error:
        return LifecycleRegister(artifact="none"), (
            f"lifecycle register not readable ({error}); findings "
            f"are not grounded against one"
        )


# The governed resource-priority definition, the same file
# `aistack.cli.resource_priority_monitor` reads.
#
# **Optional, the same way the lifecycle register is.** Criterion
# 4.1 asks whether AIStack can flag a container nobody has
# classified; a host with no definition yet has classified nothing
# at all, which is a fact worth reporting, not a reason to refuse
# the rest of the diagnosis.
DEFAULT_RESOURCE_PRIORITY = (
    Path(__file__).resolve().parents[1]
    / "priority"
    / "definitions"
    / "resource_priority.yml"
)


def resource_priority_definition(
    path: Path,
) -> tuple[ResourcePriorityDefinition | None, str]:
    """
    Read the resource-priority definition at `path`, or `None` with
    a note explaining why — never raises.

    `STD-0300` § VS-4 criterion 4.1 needs this to know which
    containers are already declared; without it, "undeclared" cannot
    be told from "everything is undeclared because nothing loaded".
    """

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


# The two containers this repository actually builds, and the
# Dockerfile each one's `CMD` is read from.
#
# **This is all of it, and it is not a coincidence.** `STD-0300` §
# VS-4 criterion 4.2's "deployment definition" needs an artifact
# this repository can read; the owner's other ~60 containers are
# deployed and managed entirely outside it (confirmed 2026-09-04),
# so no path exists here to read for them. Extending this mapping to
# another container happens when the owner names where its own
# definition lives, per `GOV-P-001` — not by guessing a path that
# looks plausible.
KNOWN_DEPLOYMENT_DEFINITIONS = {
    "aistack-selection-ui": (
        Path(__file__).resolve().parents[3] / "Dockerfile.selection-ui"
    ),
    "aistack-core": Path(__file__).resolve().parents[3] / "Dockerfile",
}


def deployment_definitions() -> dict[str, tuple[str, str]]:
    """
    `container -> (command, reference)` for every container
    `KNOWN_DEPLOYMENT_DEFINITIONS` names a readable file for.

    A file that does not exist, or declares no `CMD` at all, is
    simply absent from the returned mapping —
    `correlate_findings`/`CorrelatedFinding` already treat that as
    the real, declared state it is, not an error to raise here.
    """

    resolved: dict[str, tuple[str, str]] = {}

    for container, path in KNOWN_DEPLOYMENT_DEFINITIONS.items():
        if not path.exists():
            continue

        command = extract_dockerfile_command(
            path.read_text(encoding="utf-8")
        )

        if command is not None:
            resolved[container] = (command, f"{path.name}:CMD")

    return resolved


# How much of an evidence line the report prints.
#
# It was 90 until the first complete run, on 2026-08-22, showed
# what 90 costs: an nginx line carrying Docker's timestamp, the
# container's own timestamp and nginx's own timestamp reached
# `connect() failed (1` and stopped — the pattern that fired the
# rule, `connection refused`, was outside the extract. A piece of
# evidence that does not show what it proves.
#
# 200 covered that line and moved the boundary rather than
# removing it: a verbose enough log would put a match beyond it
# again. Since 2026-08-23 the extract is centred on the match
# instead of taken from the start, so the width bounds how much
# context is shown and no longer decides whether the pattern is
# visible at all.
EVIDENCE_WIDTH = 200


USAGE = (
    "usage: python -m aistack.cli.runtime_diagnose "
    "[--catalogue PATH] [container ...]\n"
    "\n"
    "  With no container named, every container is examined —\n"
    "  STD-0300 § VS-4 criterion 4.1 asks for detection without\n"
    "  being pointed at a service.\n"
)


def parse(argv: list[str]) -> tuple[Path, list[str]]:

    catalogue = DEFAULT_CATALOGUE
    subjects: list[str] = []
    rest = list(argv)

    while rest:
        argument = rest.pop(0)

        if argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)

        if argument == "--catalogue":
            if not rest:
                print("--catalogue expects a path")
                raise SystemExit(2)
            catalogue = Path(rest.pop(0))
            continue

        subjects.append(argument)

    return catalogue, subjects


def containers(provider: DockerProvider) -> dict[str, str]:
    """
    Every container the host declares, with its state.

    A stopped container is a subject: its last lines are often
    the only statement it ever made about why it stopped. The
    state travels with it, because whether a rule means anything
    in that state is declared by the rule.

    A container whose state Docker does not report is carried as
    `unknown` — a governed state under FDN-0003 Article 12 —
    rather than assumed to be running. Only signatures declaring
    `any` will then apply to it, which is the honest outcome.
    """

    observed = provider.collect()["docker"]["containers"]

    return {
        entry["Names"]: (entry.get("State") or "unknown")
        for entry in observed
        if isinstance(entry, dict) and entry.get("Names")
    }


def extract(text: str, match_at: int | None) -> str:
    """
    The part of a line a reader needs, around what fired the rule.

    A line that fits is printed whole. A longer one is centred on
    the match, so the pattern is visible whatever its position —
    which is the difference between an extract and a prefix.

    **What is cut is counted on the side it was cut from.** The
    heritage already refuses to trim the number of evidence lines
    in silence; the same rule applies inside a line, and a leading
    ellipsis that did not say how much it hid would misplace the
    match in the reader's head.

    `match_at` of `None` means the pattern is present and its
    position could not be determined — a folded comparison whose
    indices do not map back. The extract then starts at the
    beginning and says so by omission rather than centring on a
    position nobody computed.
    """

    if len(text) <= EVIDENCE_WIDTH:
        return text

    if match_at is None:
        return f"{text[:EVIDENCE_WIDTH]}… [+{len(text) - EVIDENCE_WIDTH}]"

    # Centre the window, then push it back inside the line. A
    # match near either end would otherwise waste half the width
    # on nothing.
    start = max(0, match_at - EVIDENCE_WIDTH // 2)
    start = min(start, len(text) - EVIDENCE_WIDTH)

    shown = text[start : start + EVIDENCE_WIDTH]

    head = f"[{start} cut] …" if start else ""
    tail_cut = len(text) - (start + EVIDENCE_WIDTH)
    tail = f"… [{tail_cut} cut]" if tail_cut else ""

    return f"{head}{shown}{tail}"


def report(
    findings: list[RuntimeFinding],
    unobserved: list[tuple[str, str]],
    catalogue: SignatureCatalogue,
    examined: int,
    states: dict[str, str],
    lifecycle_note: str = "",
    consumption: tuple[UnexplainedConsumption, ...] = (),
    resource_note: str = "",
    development_flags: tuple[DevelopmentFlagFinding, ...] = (),
    commands_note: str = "",
    correlated: tuple[CorrelatedFinding, ...] = (),
) -> None:

    print("Runtime Diagnosis Report")
    print(f"- Catalogue: {catalogue.artifact}")
    print(f"- Signatures: {len(catalogue.signatures)}")
    print(f"- Subjects examined: {examined}")
    print(f"- Window: {catalogue.deepest} lines")

    if lifecycle_note:
        print(f"- Lifecycle: {lifecycle_note}")

    if resource_note:
        print(f"- Resource priority: {resource_note}")

    if commands_note:
        print(f"- Commands: {commands_note}")

    print("")

    if not findings:
        print("No finding.")
        print("")

    for finding in findings:
        print(
            f"[{finding.subject} · {states.get(finding.subject, 'unknown')}] "
            f"{finding.signature}"
        )
        print(f"    {finding.interpretation}")
        print(f"    -> {finding.remediation}")
        print(
            f"    confidence: {finding.confidence}   "
            f"grounding: {finding.grounding}"
        )
        print(f"    evidence: {len(finding.evidence)} line(s)")

        for line in finding.evidence[:3]:
            entry = line.entry
            when = (
                entry.timestamp.isoformat(timespec="seconds")
                if entry.timestamp
                else "no timestamp"
            )
            print(
                f"      -{entry.offset}  {when}  "
                f"{extract(line.entry.text, line.match_at)}"
            )

        if len(finding.evidence) > 3:
            # Named, never silent: a report that trimmed without
            # saying so would read as complete.
            print(
                f"      … {len(finding.evidence) - 3} further "
                f"line(s) not shown; the finding carries them all"
            )

        print("")

    if unobserved:
        print("Not observed:")
        for subject, reason in unobserved:
            print(f"    {subject}: {reason}")
        print("")

    if consumption:
        print("Unexplained consumption:")
        for item in consumption:
            print(
                f"    {item.container}: {item.cpu_percent:.1f}% "
                f"(threshold {item.threshold_percent:.1f}%) — not in "
                f"resource_priority.yml"
            )
        print("")

    if development_flags:
        print("Development options enabled:")
        for item in development_flags:
            print(f"    [{item.container}] {item.pattern}")
            print(f"        {item.interpretation}")
            print(f"        command: {item.command}")
        print("")

    if correlated:
        print("Correlated evidence:")
        for item in correlated:
            print(f"    [{item.container}]")
            print(
                f"        container    {item.container_command!r}  "
                f"({item.container_reference})"
            )
            print(
                f"        process      {item.process_command!r}  "
                f"({item.process_reference})"
            )
            if item.deployment_command is not None:
                print(
                    f"        deployment   {item.deployment_command!r}  "
                    f"({item.deployment_reference})"
                )
            else:
                print(
                    "        deployment   undeclared — no readable "
                    "definition for this container"
                )
        print("")

    print(
        f"findings: {len(findings)}   "
        f"unobserved: {len(unobserved)}   "
        f"unexplained consumption: {len(consumption)}   "
        f"development options: {len(development_flags)}   "
        f"correlated: {len(correlated)}"
    )


def main() -> None:

    path, named = parse(sys.argv[1:])

    if not path.exists():
        print(f"Catalogue not found: {path}")
        print("An installed AIStack does not ship docs/; pass --catalogue.")
        raise SystemExit(2)

    try:
        catalogue = read_signature_catalogue(
            path.read_text(encoding="utf-8")
        )
    except CatalogueError as error:
        print(f"Catalogue not readable: {error}")
        raise SystemExit(2) from error

    provider = DockerProvider()

    try:
        declared = containers(provider)
    except (subprocess.SubprocessError, OSError, KeyError) as error:
        print(f"Docker could not be observed: {error}")
        raise SystemExit(2) from error

    subjects = named or list(declared)

    findings: list[RuntimeFinding] = []
    unobserved: list[tuple[str, str]] = []

    for subject in subjects:
        try:
            observation = provider.collect_logs(
                subject,
                catalogue.deepest,
                declared.get(subject, "unknown"),
            )
        except (subprocess.SubprocessError, OSError) as error:
            unobserved.append((subject, str(error).strip()[:120]))
            continue

        findings.extend(qualify(observation, catalogue))

    register, note = lifecycle_register(DEFAULT_LIFECYCLE_REGISTER)
    findings = list(ground_findings(findings, register))

    definition, resource_note = resource_priority_definition(
        DEFAULT_RESOURCE_PRIORITY
    )
    consumption: tuple[UnexplainedConsumption, ...] = ()

    if definition is not None:
        try:
            readings = provider.collect_cpu_readings()
        except (subprocess.SubprocessError, OSError) as error:
            resource_note = (
                f"CPU readings could not be collected ({error}); "
                f"consumption is not checked"
            )
        else:
            consumption = find_unexplained_consumption(readings, definition)

    development_flags: tuple[DevelopmentFlagFinding, ...] = ()
    commands_note = ""
    commands: dict[str, str] = {}

    try:
        commands = provider.collect_commands()
    except (subprocess.SubprocessError, OSError) as error:
        commands_note = (
            f"container commands could not be collected ({error}); "
            f"development options are not checked"
        )
    else:
        development_flags = find_development_flags(commands)

    # 4.2 correlates a subject a prior check already named — never a
    # fresh sweep of the host, since `docker top` takes one container
    # at a time and sixty findings nobody asked for is not the point.
    to_correlate = {item.container for item in development_flags} | {
        item.container for item in consumption
    }

    processes = {
        name: provider.collect_process(name) for name in to_correlate
    }

    correlated = correlate_findings(
        to_correlate, commands, processes, deployment_definitions()
    )

    report(
        findings,
        unobserved,
        catalogue,
        len(subjects),
        declared,
        note,
        consumption,
        resource_note,
        development_flags,
        commands_note,
        correlated,
    )

    # A subject that could not be read makes the sweep partial,
    # and a partial sweep reporting "no finding" would be read as
    # "nothing is wrong". That outranks the findings themselves:
    # 2 says the run did not do what it was asked.
    if unobserved:
        raise SystemExit(2)

    if findings or consumption or development_flags:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
