from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from aistack.ai_runtime import call_journal
from aistack.ai_runtime.call_journal import append, call_of, journaled, read
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer

SECRET_PROMPT = "PROMPT-WITH-A-HOST-NAME nas-01.lan"
SECRET_RESPONSE = "RESPONSE-WITH-A-PATH /srv/aistack/secret"


def answer(**changes) -> AIRuntimeAnswer:
    base = AIRuntimeAnswer(
        operation="reason",
        subject="host.disk",
        model="qwen2.5:7b",
        prompt=SECRET_PROMPT,
        response=SECRET_RESPONSE,
        reachable=True,
        language="fr",
    )
    return replace(base, **changes)


def test_a_line_names_who_asked_and_who_answered(tmp_path):
    asked = journaled(lambda *a, **k: answer(), call_journal.SECURITY_PAGE, tmp_path)

    asked("finding", "reason", "fr")

    (line,) = read(tmp_path)
    assert (line.caller, line.operation, line.language) == ("security.page", "reason", "fr")
    assert (line.answered_by, line.reachable, line.reached_external) == ("qwen2.5:7b", True, False)
    assert line.seconds >= 0


def test_the_journal_never_holds_the_prompt_or_the_response(tmp_path):
    journaled(lambda *a, **k: answer(), "troubleshooting", tmp_path)("f", "reason", "fr")

    text = (tmp_path / call_journal.JOURNAL_FILE).read_text(encoding="utf-8")

    assert "nas-01" not in text and "secret" not in text and SECRET_PROMPT not in text


def test_the_answer_comes_back_unchanged(tmp_path):
    given = answer()

    assert journaled(lambda *a, **k: given, "troubleshooting", tmp_path)("f", "reason", "fr") is given


def test_a_question_that_went_outside_is_marked_even_when_a_local_engine_answered(tmp_path):
    asked = journaled(lambda *a, **k: answer(model="qwen2.5:7b (Gemini: down)", external=True), "troubleshooting", tmp_path)

    asked("f", "reason", "fr")

    assert read(tmp_path)[0].reached_external is True


def test_what_was_set_aside_is_kept_and_bounded(tmp_path):
    reason = "olala answer set aside twice, it broke the rules: " + "x" * 1000
    silent = answer(reachable=False, response="", unreachable_reason=reason)

    journaled(lambda *a, **k: silent, "vigil.reason", tmp_path)("f", "reason", "fr")

    (line,) = read(tmp_path)
    assert line.reachable is False
    assert line.set_aside.startswith("olala answer set aside twice")
    assert len(line.set_aside) == call_journal.REASON_LIMIT


def test_a_call_goes_on_when_the_journal_cannot_be_written(tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding="utf-8")
    given = answer()

    assert journaled(lambda *a, **k: given, "troubleshooting", blocked / "ai-calls")("f", "reason", "fr") is given


def test_read_gives_the_newest_first_and_skips_broken_lines(tmp_path):
    for index in range(3):
        append(tmp_path, replace(call_of("a", answer(), 1.0), operation=f"op{index}"))
    with (tmp_path / call_journal.JOURNAL_FILE).open("a", encoding="utf-8") as stream:
        stream.write("not json\n")

    assert [c.operation for c in read(tmp_path, limit=2)] == ["op2", "op1"]


def test_the_journal_drops_what_is_older_than_ninety_days_once_it_is_long(tmp_path, monkeypatch):
    monkeypatch.setattr(call_journal, "TRIM_AT", 3)
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
    old = (now - timedelta(days=call_journal.KEPT_DAYS + 1)).isoformat()
    fresh = (now - timedelta(days=1)).isoformat()
    path = tmp_path / call_journal.JOURNAL_FILE
    base = call_of("a", answer(), 1.0)
    path.write_text(
        "\n".join(json.dumps({**vars(base), "at": at}) for at in (old, old, fresh)) + "\n", encoding="utf-8"
    )

    append(tmp_path, replace(base, at=fresh), today=now)

    assert [c.at for c in read(tmp_path)] == [fresh, fresh]


def test_a_gemini_question_is_marked_external(monkeypatch):
    from aistack.troubleshooting import guide

    calls = []

    class Declared:
        gemini = openai = anthropic = None

    class Gemini:
        model = "gemini-test"

    monkeypatch.setattr(guide, "load_ai_runtime_yaml", lambda path: Declared())
    monkeypatch.setattr(guide, "_gemini", lambda definition: Gemini())
    monkeypatch.setitem(guide._CALLS, "reason", lambda finding, engine, label, **k: calls.append(label) or answer(model=label))

    result = guide.ask_ai_runtime(None, "reason", "fr")

    assert result.external is True and result.reachable


def test_a_local_only_question_is_not_marked_external(monkeypatch):
    from aistack.troubleshooting import guide

    class Declared:
        gemini = openai = anthropic = None

    monkeypatch.setattr(guide, "load_ai_runtime_yaml", lambda path: Declared())
    monkeypatch.setattr(guide, "_gemini", lambda definition: None)
    monkeypatch.setattr(guide, "ask_local", lambda *a, **k: answer())

    assert guide.ask_ai_runtime(None, "reason", "fr").external is False
