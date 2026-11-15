from __future__ import annotations

import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from aistack.restart_watch.definition import Probe
from aistack.restart_watch.facts import ContainerFacts, Run, read_facts, run_docker

Sleep = Callable[[float], None]
Clock = Callable[[], float]
Ask = Callable[[Probe], bool]


@dataclass(frozen=True)
class Outcome:
    """What restarting one container led to; `ok` is False when it did not come back."""

    name: str
    ok: bool
    detail: str = ""


def ask(probe: Probe) -> bool:
    """A probe's verdict: alive when anything under 500 answers."""

    request = urllib.request.Request(probe.url, headers={"User-Agent": "AIStack-restart-watch"})

    try:
        with urllib.request.urlopen(request, timeout=probe.timeout_seconds) as answer:  # noqa: S310 — the owner's own address
            return bool(answer.status < 500)
    except urllib.error.HTTPError as error:
        return error.code < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def failed_probes(probes: Mapping[str, Probe], ask_probe: Ask = ask) -> frozenset[str]:
    """The names whose declared probe got no answer."""

    return frozenset(name for name, probe in probes.items() if not ask_probe(probe))


def restart_in_order(
    order: Sequence[str],
    probes: Mapping[str, Probe],
    wait_seconds: float,
    run: Run = run_docker,
    sleep: Sleep = time.sleep,
    clock: Clock = time.monotonic,
    ask_probe: Ask = ask,
    dry_run: bool = False,
) -> tuple[Outcome, ...]:
    """
    Restart `order` one by one, each only once the previous one answers.

    A container "answers" when it runs and — by what it has — its
    healthcheck says healthy, or its declared probe replies; one with
    neither only has to stay running for a few seconds. The first one that
    does not come back within `wait_seconds` ends the plan: restarting
    what depends on it would only add to the damage.
    """

    outcomes: list[Outcome] = []

    for name in order:
        if dry_run:
            outcomes.append(Outcome(name, True, "dry run"))
            continue

        done = run(["restart", name])

        if done.returncode != 0:
            outcomes.append(Outcome(name, False, done.stderr.strip() or "docker restart failed"))
            break

        verdict = _wait_until_back(name, probes.get(name), wait_seconds, run, sleep, clock, ask_probe)
        outcomes.append(verdict)

        if not verdict.ok:
            break

    return tuple(outcomes)


def _wait_until_back(
    name: str,
    probe: Probe | None,
    wait_seconds: float,
    run: Run,
    sleep: Sleep,
    clock: Clock,
    ask_probe: Ask,
) -> Outcome:
    started = clock()
    last = "not running"

    while True:
        try:
            current = next((item for item in read_facts(run) if item.name == name), None)
        except (RuntimeError, ValueError, OSError) as error:
            current, last = None, str(error)

        if current is not None:
            if not current.running:
                last = "not running"
            elif current.has_healthcheck:
                last = f"health: {current.health}"

                if current.health == "healthy":
                    return Outcome(name, True, "healthy")
            elif probe is not None:
                last = "probe: no answer"

                if ask_probe(probe):
                    return Outcome(name, True, "probe answered")
            elif clock() - started >= 10.0:
                return Outcome(name, True, "running")
            else:
                last = "running, not yet settled"

        if clock() - started >= wait_seconds:
            return Outcome(name, False, f"still {last} after {int(wait_seconds)} s")

        sleep(3.0)


def container_names(facts: Sequence[ContainerFacts]) -> frozenset[str]:
    return frozenset(item.name for item in facts)
