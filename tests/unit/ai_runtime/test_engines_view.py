"""What the page *Moteurs IA* is built from: the engines and their last seen, the counts, the silences read from a route."""

from __future__ import annotations

from aistack.ai_runtime.call_journal import Call
from aistack.ai_runtime.definition import AIRuntimeDefinition, GeminiDefinition, HostedDefinition, LocalEngineDefinition
from aistack.ai_runtime.engines_view import NO_KEY, NOT_DECLARED, READY, answerer, build, silent_of
from aistack.ai_runtime.policy import AIPolicy, Preference

QWEN = LocalEngineDefinition("ollama", "127.0.0.1", 11434, "qwen2.5:7b")
OLALA = LocalEngineDefinition("openai_chat", "192.168.1.10", 8080, "olala-mini", label="Olala")
BIG = LocalEngineDefinition("openai_chat", "api.example.com", 443, "big")

POLICY = AIPolicy(
    {"troubleshooting": "external_allowed", "security.page": "internal_only"},
    kinds={"reason": "diagnosis"},
    preferences={"diagnosis": (Preference("anthropic", "long reasoning"), Preference("local", "stays home"))},
)


def call(at: str, caller="troubleshooting", answered_by="anthropic:claude-x", reachable=True, external=True, seconds=2.0,
         route="", kind="diagnosis") -> Call:
    return Call(at, caller, "reason", "fr", answered_by, external, reachable, seconds, "", "external_allowed", False, route, kind)


def definition(**more) -> AIRuntimeDefinition:
    return AIRuntimeDefinition(host="127.0.0.1", port=11434, model="qwen", engines=(QWEN, OLALA), **more)


def test_a_silence_is_read_from_the_route():
    route = "external_allowed; kind=diagnosis; chose gemini: fast; silent: anthropic (Claude refused the request with status 529), openai (ChatGPT refused); passed over: x (not declared)"

    assert silent_of(route) == (
        ("anthropic", "Claude refused the request with status 529"),
        ("openai", "ChatGPT refused"),
    )
    assert silent_of("internal_only; chose local: x") == ()
    assert silent_of("") == ()


def test_the_engine_that_answered_is_what_comes_before_the_silent_ones():
    assert answerer(call("t", answered_by="gemini:g-x (Claude: refused ; ChatGPT: no credits)")) == "gemini:g-x"
    assert answerer(call("t", answered_by="qwen2.5:7b")) == "qwen2.5:7b"
    assert answerer(call("t", answered_by="")) == "—"


def test_the_engines_say_ready_no_key_or_not_declared_and_where_they_are():
    view = build(POLICY, definition(gemini=GeminiDefinition("g-x"), anthropic=HostedDefinition("c-x", "K")), ["gemini"], ())

    states = {row.key: row.state for row in view.engines}
    assert states == {"qwen2.5:7b": READY, "Olala": READY, "gemini": READY, "openai": NOT_DECLARED, "anthropic": NO_KEY}
    rows = {row.key: row for row in view.engines}
    assert rows["Olala"].where == "192.168.1.10:8080" and rows["Olala"].outside is False
    assert rows["gemini"].outside is True and rows["gemini"].where == ""
    assert rows["anthropic"].model == "c-x" and rows["openai"].model == ""


def test_a_local_engine_on_a_public_address_is_shown_outside():
    row = build(POLICY, AIRuntimeDefinition(host="h", port=1, engines=(BIG,)), [], ()).engines[0]

    assert row.outside is True


def test_each_engine_shows_when_it_last_answered_and_when_it_last_stayed_silent():
    calls = (
        call("2026-11-21T09:40:00+00:00", answered_by="gemini:g-x (Claude: x)", route="external_allowed; silent: anthropic (status 529)"),
        call("2026-11-21T09:30:00+00:00", answered_by="anthropic:claude-x", seconds=5.8),
        call("2026-11-21T09:20:00+00:00", answered_by="qwen2.5:7b", external=False, seconds=21.0, caller="security.page"),
    )
    view = build(POLICY, definition(gemini=GeminiDefinition("g-x"), anthropic=HostedDefinition("c-x", "K")), ["gemini", "anthropic"], calls)
    rows = {row.key: row for row in view.engines}

    assert rows["anthropic"].last_answered == "2026-11-21T09:30:00+00:00" and rows["anthropic"].last_seconds == 5.8
    assert rows["anthropic"].last_silent_at == "2026-11-21T09:40:00+00:00" and rows["anthropic"].last_silent_why == "status 529"
    assert rows["gemini"].last_answered == "2026-11-21T09:40:00+00:00"
    assert rows["qwen2.5:7b"].last_answered == "2026-11-21T09:20:00+00:00" and rows["qwen2.5:7b"].last_seconds == 21.0
    assert rows["openai"].last_answered == "" and rows["Olala"].last_answered == ""


def test_the_counts_by_caller_kind_and_engine_and_the_share_that_went_outside():
    calls = (
        call("3", answered_by="anthropic:claude-x", seconds=4.0),
        call("2", answered_by="anthropic:claude-x", seconds=6.0, route="x; silent: gemini (503)"),
        call("1", caller="security.page", answered_by="qwen2.5:7b", external=False, seconds=20.0, kind="explanation"),
        call("0", caller="security.page", answered_by="", reachable=False, external=False, seconds=1.0, kind="explanation"),
    )

    view = build(POLICY, definition(), [], calls)

    assert (view.total.calls, view.total.outside, view.total.unanswered, view.with_fallback) == (4, 2, 1, 1)
    assert dict(view.by_caller)["troubleshooting"].calls == 2 and dict(view.by_caller)["security.page"].unanswered == 1
    assert dict(view.by_kind)["explanation"].calls == 2 and dict(view.by_kind)["diagnosis"].average == 5.0
    assert [name for name, _ in view.by_engine][0] == "anthropic:claude-x"
    assert dict(view.by_engine)["qwen2.5:7b"].seconds == 20.0


def test_the_policy_and_the_table_are_carried_with_their_reasons_and_only_the_newest_calls_are_listed():
    calls = tuple(call(str(n)) for n in range(40))

    view = build(POLICY, definition(), [], calls, shown=30)

    assert view.callers == (("security.page", "internal_only"), ("troubleshooting", "external_allowed"))
    assert view.kinds == (("reason", "diagnosis"),)
    assert view.table[0][0] == "diagnosis" and view.table[0][1][0].why == "long reasoning"
    assert len(view.recent) == 30 and view.recent[0].at == "0"


def test_with_no_call_there_is_nothing_to_count():
    view = build(AIPolicy(), definition(), [], ())

    assert view.total.calls == 0 and view.by_caller == () and view.recent == () and view.total.average == 0.0
