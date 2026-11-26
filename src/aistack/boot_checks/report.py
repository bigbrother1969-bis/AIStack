"""What the start-up checks say, as text (ADR-0032, slice B2): the summary of a verdict and the declaration the facts suggest."""

from __future__ import annotations

from aistack.boot_checks.controls import ANOMALIES
from aistack.boot_checks.facts import BootFacts
from aistack.boot_checks.state import Verdict

# The exit code says how the start looks: 0 well (or still being checked), 1 to watch, 2 to fix, 3 not judged.
EXIT = {"ok": 0, "pending": 0, "warning": 1, "critical": 2, "unknown": 3}


def suggestion(facts: BootFacts) -> str:
    """The facts as a declaration to copy: the owner reads it and keeps what is right."""

    lines = ["# Read it, correct it, then copy it into your boot_checks.yml."]
    containers = facts.containers or ()
    running = [item.name for item in containers if item.state == "running"]
    stopped = [item.name for item in containers if item.state != "running"]
    lines.append("expected_containers: [" + ", ".join(sorted([*running, *stopped])) + "]")
    lines.append("expected_stopped: [" + ", ".join(sorted(stopped)) + "]")
    lines.append("mounts: [" + ", ".join(facts.mounts or ()) + "]")

    if facts.docker_user_rules is not None:
        lines.append(f"docker_user_rules: {facts.docker_user_rules}")

    if facts.probes:
        lines.append("probes:")
        lines.extend(f"  {label}: {status}" for label, status in sorted(facts.probes.items()))

    return "\n".join(lines)


def companion_suggestion(name: str, facts: BootFacts) -> str:
    """The mounts a companion shows, as the part of the declaration that names them."""

    return f"  {name}: [" + ", ".join(facts.mounts or ()) + "]"


def describe(verdict: Verdict, host: str | None = None) -> str:
    where = f" of {host}" if host else ""
    lines = [f"start-up checks{where}: {verdict.overall} ({verdict.anomalies} anomaly(ies)) at {verdict.checked_at}"]

    if verdict.booted_at:
        lines.append(f"  started at {verdict.booted_at}")

    if verdict.note:
        lines.append(f"  {verdict.note}")

    for result in verdict.results:
        mark = "!!" if result.status in ANOMALIES else "  "
        lines.append(f"{mark} {result.control:<17} {result.status:<11} {result.summary}")
        lines.extend(f"       - {detail}" for detail in result.details)

    resolved = [item for item in verdict.incidents if item.resolved_at]

    if resolved:
        lines.append("resolved since the start:")
        lines.extend(f"  - {item.control}: {item.summary} ({item.first_seen} to {item.resolved_at})" for item in resolved)

    return "\n".join(lines)
