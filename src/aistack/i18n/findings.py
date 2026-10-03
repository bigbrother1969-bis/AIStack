"""
A finding's sentences in the reader's language (ADR-0010 § 4, revised
2026-10-03): its `FindingMessage` rendered through the catalogs when
the evaluator declared one, its English text otherwise.
"""

from __future__ import annotations

from aistack.contracts.finding_message import MessagePart
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.i18n.translator import Translator


def render_parts(parts: tuple[MessagePart, ...], t: Translator) -> str:
    return " ".join(t(item.key, **dict(item.params)) for item in parts)


def finding_interpretation(finding: RuntimeFinding, t: Translator) -> str:
    if finding.message is None:
        return finding.interpretation

    return render_parts(finding.message.interpretation, t)


def finding_remediation(finding: RuntimeFinding, t: Translator) -> str:
    if finding.message is None:
        return finding.remediation

    return render_parts(finding.message.remediation, t)


# The confidence words evaluators write today; any other is shown as it is.
_CONFIDENCE_KEYS = {"Measured": "findings.confidence.measured"}


def finding_confidence(finding: RuntimeFinding, t: Translator) -> str:
    key = _CONFIDENCE_KEYS.get(finding.confidence)

    return t(key) if key else finding.confidence
