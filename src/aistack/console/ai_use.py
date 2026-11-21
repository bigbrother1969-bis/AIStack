"""
What a console card's screen asks of the AI engines, from the policy (`ADR-0029` § 11).

A card declares the uses of a model it reaches (`ai_callers`); the class of each comes from
`ai_policy.yml`, so the line on the card stays true when the owner changes the policy. Pure.
"""

from __future__ import annotations

from collections.abc import Iterable

from aistack.ai_runtime.policy import AIPolicy
from aistack.contracts.console_link import AI_EXTERNAL, AI_LOCAL, AI_NONE


def ai_use_of(callers: Iterable[str] | None, policy: AIPolicy) -> str:
    """
    `AI_NONE` for a screen that reaches no use of a model, `AI_EXTERNAL` when any of the uses it reaches
    may go outside (`external_allowed`), else `AI_LOCAL`. Empty when the card does not declare its uses.
    """

    if callers is None:
        return ""

    reached = tuple(callers)

    if not reached:
        return AI_NONE

    return AI_EXTERNAL if any(policy.allows_external(caller) for caller in reached) else AI_LOCAL
