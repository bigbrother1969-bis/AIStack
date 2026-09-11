"""
Governed `Normalizer[TIn, TOut]` contract — J4, Evidence and
Observation Foundation.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


class Normalizer(Protocol[TIn, TOut]):
    """
    One call, one raw argument, a canonical result back —
    `parse_sensors_output`'s own shape (`str ->
    tuple[TemperatureReading, ...]`), declared around it rather than
    renamed to fit — the same "keep the working name" reasoning
    `Collector` (`kernel/evidence/collector.py`) states in full.

    **`normalize_log_evidence` does not conform, and is not claimed
    to.** Its shape is `(raw: str, *, subject, provider, state,
    depth, collected_at) -> RuntimeObservation` — a richer
    normalizer that needs context `parse_sensors_output` does not,
    not a two-argument function this Protocol could describe without
    inventing meaning for the extra, required keyword parameters.
    `ADR-0008` already names it as the normalization stage for logs;
    this Protocol names the shape one normalizer actually has, not a
    shape wide enough to swallow both.

    **`aistack.conformance.structural.satisfies` does not measure this
    honestly, and not in the direction `Collector`'s docstring
    describes.** Rather than reporting this Protocol as an orphan, it
    reports `Normalizer[TIn, TOut]` as satisfied by every concrete
    class the inventory can import — 192, at the count this was
    found — because `getattr(some_class, "__call__")` falls through
    to the metaclass and returns `type.__call__` (what constructs an
    instance), whose signature is the generic `(*args, **kwargs)`; a
    two-parameter `__call__` with a positional-only argument matches
    that shape on both length and name for every class that defines
    no `__call__` of its own. `Collector` (one parameter, `self`
    alone) escapes this by the length check alone; `Normalizer` does
    not. This is `GOV-0002/OS-059`, left open rather than fixed here
    — a defect in a shared instrument, not in this contract.
    `Normalizer`'s real conformance is proven the way `Collector`'s
    is regardless: by `mypy src` over the assignment in
    `kernel/evidence/conformance.py`, which reads the actual call
    shape rather than a dunder name every class happens to expose.

    `raw` is declared positional-only (`/`) because its name is not
    part of this contract — `parse_sensors_output` calls its own
    parameter `text`, and `aistack.conformance.structural`'s own
    `incompatible_members` states the rule this follows: "a contract
    that does not care declares the parameter positional-only, which
    says so in the language rather than in a comment." Without it,
    `mypy` treats the parameter name itself as part of the shape and
    refuses `parse_sensors_output` for naming it differently — found
    while proving this contract's own conformance, not by inspection.
    """

    def __call__(self, raw: TIn, /) -> TOut: ...
