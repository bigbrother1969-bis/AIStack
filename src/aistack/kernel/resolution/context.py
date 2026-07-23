from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Request


@dataclass(frozen=True, slots=True)
class ResolutionContext:
    """
    Context provided to the Resolution Layer.

    The context is intentionally minimal in the first version.
    Additional resolution inputs will be introduced progressively.
    """

    request: Request
