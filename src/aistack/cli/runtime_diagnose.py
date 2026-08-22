from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.signature import SignatureCatalogue
from aistack.policies.signature_catalogue import (
    CatalogueError,
    read_signature_catalogue,
)
from aistack.providers.docker import DockerProvider
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


def report(
    findings: list[RuntimeFinding],
    unobserved: list[tuple[str, str]],
    catalogue: SignatureCatalogue,
    examined: int,
    states: dict[str, str],
) -> None:

    print("Runtime Diagnosis Report")
    print(f"- Catalogue: {catalogue.artifact}")
    print(f"- Signatures: {len(catalogue.signatures)}")
    print(f"- Subjects examined: {examined}")
    print(f"- Window: {catalogue.deepest} lines")
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

        for entry in finding.evidence[:3]:
            when = (
                entry.timestamp.isoformat(timespec="seconds")
                if entry.timestamp
                else "no timestamp"
            )
            print(f"      -{entry.offset}  {when}  {entry.text[:90]}")

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

    print(
        f"findings: {len(findings)}   "
        f"unobserved: {len(unobserved)}"
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

    report(findings, unobserved, catalogue, len(subjects), declared)

    # A subject that could not be read makes the sweep partial,
    # and a partial sweep reporting "no finding" would be read as
    # "nothing is wrong". That outranks the findings themselves:
    # 2 says the run did not do what it was asked.
    if unobserved:
        raise SystemExit(2)

    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
