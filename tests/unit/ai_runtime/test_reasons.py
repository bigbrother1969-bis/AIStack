"""The reason of a choice, said in the language of the page (ADR-0029 § 10); the journal keeps one text."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.ai_runtime import choice, policy, reasons
from aistack.ai_runtime.policy import load_ai_policy

LOCAL = "stays on your machines: nothing you typed leaves the house"
LOCAL_FR = "reste sur tes machines : rien de ce que tu as écrit ne sort de la maison"


def declared(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ai_policy.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_shipped_reasons_are_written_in_every_language_the_interface_has():
    shipped = load_ai_policy(policy.SHIPPED)

    for lines in shipped.preferences.values():
        for line in lines:
            assert dict(line.by_language).keys() == {"fr", "en"}, line
            assert line.why == dict(line.by_language)["en"], "the journal keeps the English text"


def test_a_reason_is_said_in_the_language_asked():
    assert reasons.localize(LOCAL, "fr") == LOCAL_FR
    assert reasons.localize(LOCAL, "en") == LOCAL


def test_a_route_of_the_journal_is_said_in_french_reason_by_reason():
    route = f"internal_only; kind=question; chose qwen2.5:7b: {LOCAL}; passed over: gemini (key not set)"

    said = reasons.localize(route, "fr")

    assert LOCAL_FR in said and LOCAL not in said
    assert said.startswith("internal_only; kind=question; chose qwen2.5:7b: ") and said.endswith("passed over: gemini (key not set)")


def test_the_order_declared_is_said_in_french_too():
    assert reasons.localize(f"chose local: {choice.DECLARED_ORDER}", "fr") == "chose local: ordre déclaré"


def test_a_copy_made_before_the_translation_reads_in_french_without_being_edited(tmp_path: Path):
    copy = load_ai_policy(
        declared(
            tmp_path,
            f"callers: {{portal.chat: external_allowed}}\n"
            f"preferences:\n  question:\n    - {{engine: local, why: \"{LOCAL}\"}}\n",
        )
    )

    assert copy.preferences["question"][0].by_language == ()
    assert reasons.localize(LOCAL, "fr", copy) == LOCAL_FR


def test_a_reason_the_owner_wrote_is_shown_as_written_and_wins_over_the_shipped_one(tmp_path: Path):
    mine = load_ai_policy(
        declared(
            tmp_path,
            "preferences:\n  question:\n    - {engine: local, why: {en: \"my own reason\", fr: \"ma raison\"}}\n"
            f"    - {{engine: gemini, why: \"{LOCAL}\"}}\n",
        )
    )

    assert reasons.localize("chose local: my own reason", "fr", mine) == "chose local: ma raison"
    assert reasons.localize("an unknown reason", "fr", mine) == "an unknown reason"
    assert reasons.localize("", "fr", mine) == ""


def test_a_language_no_reason_was_written_in_leaves_the_text_as_it_was():
    assert reasons.localize(LOCAL, "de") == LOCAL
    assert reasons.localize(LOCAL, None) == LOCAL


@pytest.mark.parametrize(
    "text",
    [
        "preferences:\n  question:\n    - {engine: local, why: {en: \"only english\"}}\n",
        "preferences:\n  question:\n    - {engine: local, why: {fr: \"x\", xx: \"y\"}}\n",
        "preferences:\n  question:\n    - {engine: local, why: {fr: \"\"}}\n",
        "preferences:\n  question:\n    - {engine: local, why: 3}\n",
    ],
)
def test_a_reason_in_several_languages_must_name_the_reference_language_and_real_ones(tmp_path: Path, text: str):
    with pytest.raises(ValueError):
        load_ai_policy(declared(tmp_path, text))
