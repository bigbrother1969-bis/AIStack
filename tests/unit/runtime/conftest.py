"""
Every finding an evaluator test builds is also checked against the
catalogs (ADR-0010 § 4, revised 2026-10-03): when it carries a
`FindingMessage`, the English catalog must render it to exactly the
evaluator's own English sentences, and every other declared language
must render it with no placeholder left unfilled. Done here, around the
constructor, so each branch the evaluator tests already reach is
checked — no second set of fixtures to keep in step.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.i18n import default_languages, translator_for
from aistack.i18n.findings import render_parts

CHECKED: list[str] = []


@pytest.fixture(autouse=True)
def every_finding_speaks_every_language(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    original = RuntimeFinding.__post_init__

    def checked(self: RuntimeFinding) -> None:
        original(self)

        if self.message is None:
            return

        english = translator_for("en")
        assert render_parts(self.message.interpretation, english) == self.interpretation
        assert render_parts(self.message.remediation, english) == self.remediation

        for code in default_languages().codes():
            t = translator_for(code)
            for text in (
                render_parts(self.message.interpretation, t),
                render_parts(self.message.remediation, t),
            ):
                assert "{" not in text and "}" not in text, (code, text)

        CHECKED.extend(item.key for item in (*self.message.interpretation, *self.message.remediation))

    monkeypatch.setattr(RuntimeFinding, "__post_init__", checked)
    yield
