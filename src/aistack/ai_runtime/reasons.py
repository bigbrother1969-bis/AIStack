"""
The reason a call was routed as it was, in the language of the page (ADR-0029 § 10).

The journal keeps one text per reason (the English one) so that it reads the same whatever language
the page that wrote it was in. A page that shows a reason says it in its own language: the policy's lines
carry their text in each language they were written in (`Preference.by_language`), and a reason is looked
up there. A copy of `ai_policy.yml` made before the lines were translated holds plain English texts: they
are looked up in the shipped file too, so the page of a copy that was never edited reads in French as well.
A reason the owner wrote in one language only is shown as written.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from aistack.ai_runtime.choice import DECLARED_ORDER
from aistack.ai_runtime.policy import SHIPPED, AIPolicy, current_policy, load_ai_policy

# The reasons the code gives itself, not read from a file.
BUILT_IN: dict[str, dict[str, str]] = {DECLARED_ORDER: {"fr": "ordre déclaré"}}


def _table(policy: AIPolicy, shipped: AIPolicy) -> list[tuple[str, dict[str, str]]]:
    found: dict[str, dict[str, str]] = {key: dict(words) for key, words in BUILT_IN.items()}

    for source in (shipped, policy):  # the declaration in use wins over the shipped file
        for lines in source.preferences.values():
            for line in lines:
                if line.by_language:
                    found[line.why] = {**found.get(line.why, {}), **dict(line.by_language)}

    return sorted(found.items(), key=lambda item: -len(item[0]))


def localize(text: str, lang: str | None, policy: AIPolicy | None = None, shipped: Path | None = None) -> str:
    """
    `text` (a reason, or a route holding reasons) with each reason known in `lang` said in it. Text that
    holds no known reason, or a language no reason was written in, comes back as it was.
    """

    if not text or not lang:
        return text

    try:
        base = load_ai_policy(shipped or SHIPPED)
    except (OSError, ValueError, yaml.YAMLError):
        return text

    for reason, words in _table(policy if policy is not None else current_policy(), base):
        if lang in words and reason in text:
            text = text.replace(reason, words[lang])

    return text
