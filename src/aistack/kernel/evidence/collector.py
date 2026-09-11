"""
Governed `Collector[T]` contract — J4, Evidence and Observation
Foundation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

T = TypeVar("T", covariant=True)


class Collector(Protocol[T]):
    """
    One call, zero arguments, a sequence of `Evidence` back — the
    shape `DockerProvider.collect_cpu_readings` and
    `HostProvider.collect_temperatures` already have.

    Declared as a callable Protocol (`__call__`, not a named method
    every implementation must adopt) on purpose: the two real
    collectors keep their own names, each already meaningful and
    already the name whatever calls them expects — STD-P-002's
    "sans réécrire ce qui marche" forbids renaming a working method
    to fit a contract. A bound method satisfies `__call__` by being
    itself callable with that shape; nothing is renamed to declare
    this.

    **`aistack.conformance.structural.satisfies` cannot see this
    conformance, and that is stated here rather than worked around.**
    That check compares *classes* — `DockerProvider`, `HostProvider`
    — for a member literally named `__call__`; neither class defines
    one, so `contract-debt` publishes `Collector[T]` as an orphan the
    day it is declared, correctly, by the only measurement that tool
    takes. What actually holds is a narrower, different claim: *the
    bound method itself*, not its class, has the right call shape —
    proven by `mypy src`'s static check of the assignments in
    `kernel/evidence/conformance.py`, and exercised at runtime by
    this package's own tests. `GOV-0002/OS-001` records this
    distinction where the contract is qualified, the same entry that
    once qualified `EvidenceCollector` — the heavier, unimplemented
    contract this one and `Normalizer` replace.

    **`Normalizer` (`kernel/evidence/normalizer.py`) is measured by
    that same tool, and wrongly, in the opposite direction — reported
    satisfied by nearly every class in the package rather than by
    none.** The two Protocols differ only in parameter count
    (`Collector.__call__` takes zero beyond `self`, `Normalizer
    .__call__` takes one), and it is that difference, not this one's
    own reasoning, that decides which false result each gets — see
    `Normalizer`'s docstring and `GOV-0002/OS-059`.

    Three of `DockerProvider`'s own methods — `collect_logs`,
    `collect_commands`, `collect_process` — do **not** conform, and
    are not claimed to: `collect_logs` takes three required
    arguments and returns an `Observation`, not a
    `Sequence[Evidence]`; `collect_commands`/`collect_process`
    return raw, pre-`Evidence` data (`dict[str, str]`, `str`) with no
    evidence contract of their own yet. Forcing a fourth or fifth
    arity into one shape to call every provider method uniform would
    be the rewrite this milestone forbids; naming three real
    exceptions is what keeping the shape honest costs instead.
    """

    def __call__(self) -> Sequence[T]: ...
