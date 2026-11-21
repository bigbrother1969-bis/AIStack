"""`plan`: which engines a call asks, in which order, and what it passes over (ADR-0029 § 10)."""

from __future__ import annotations

from aistack.ai_runtime.choice import Step, plan, route_of
from aistack.ai_runtime.definition import LocalEngineDefinition
from aistack.ai_runtime.policy import AIPolicy, Preference

QWEN = LocalEngineDefinition("ollama", "127.0.0.1", 11434, "qwen2.5:7b")
OLALA = LocalEngineDefinition("openai_chat", "127.0.0.1", 8080, "olala-mini", label="Olala")
BIG = LocalEngineDefinition("openai_chat", "api.example.com", 443, "big")
ALL = ("gemini", "openai", "anthropic")


def policy(caller_class: str = "external_allowed", table=None) -> AIPolicy:
    table = table if table is not None else {
        "diagnosis": (
            Preference("anthropic", "long reasoning"),
            Preference("openai", "second opinion"),
            Preference("gemini", "fast"),
            Preference("local", "stays home"),
        )
    }
    return AIPolicy({"c": caller_class}, kinds={"reason": "diagnosis"}, preferences=table)


def names(steps):
    return [step.engine for step in steps]


def test_the_best_engine_of_the_kind_is_first_and_says_why():
    steps, passed = plan(policy(), "c", "diagnosis", ALL, ALL, (QWEN,))

    assert names(steps) == ["anthropic", "openai", "gemini", "local"]
    assert steps[0].why == "long reasoning" and passed == ()


def test_an_engine_not_set_or_not_declared_is_passed_over_with_the_reason():
    steps, passed = plan(policy(), "c", "diagnosis", ("gemini", "anthropic"), ("gemini",), (QWEN,))

    assert names(steps) == ["gemini", "local"]
    assert passed == ("anthropic (key not set)", "openai (not declared)")


def test_the_class_is_a_ceiling_whatever_the_table_ranks():
    steps, passed = plan(policy("internal_only"), "c", "diagnosis", ALL, ALL, (QWEN, BIG))

    assert names(steps) == ["local"] and steps[0].local == (QWEN,)
    assert "gemini (not allowed for this caller)" in passed
    assert "big (outside your machines, not allowed for this caller)" in passed


def test_a_caller_the_policy_does_not_name_is_internal():
    steps, _ = plan(policy(), "stranger", "diagnosis", ALL, ALL, (QWEN,))

    assert names(steps) == ["local"]


def test_a_local_engine_can_be_named_by_its_label_or_its_model():
    table = {"diagnosis": (Preference("olala", "steady"), Preference("qwen2.5:7b", "fast"))}

    steps, _ = plan(policy(table=table), "c", "diagnosis", (), (), (QWEN, OLALA))

    assert names(steps) == ["Olala", "qwen2.5:7b"] and steps[0].local == (OLALA,)


def test_a_named_local_engine_that_is_not_declared_is_passed_over():
    table = {"diagnosis": (Preference("ghost", "x"), Preference("local", "home"))}

    steps, passed = plan(policy(table=table), "c", "diagnosis", (), (), (QWEN,))

    assert names(steps) == ["local"] and passed == ("ghost (not declared)",)


def test_a_kind_with_no_list_falls_back_to_the_order_declared_within_the_ceiling():
    steps, _ = plan(policy(), "c", "unlisted", ALL, ("openai", "gemini"), (QWEN,))
    assert names(steps) == ["gemini", "openai", "local"] and steps[0].why == "declared order"

    steps, _ = plan(policy("internal_only"), "c", "unlisted", ALL, ALL, (QWEN,))
    assert names(steps) == ["local"]


def test_a_list_that_leaves_no_engine_falls_back_instead_of_asking_nothing():
    table = {"diagnosis": (Preference("anthropic", "only this one"),)}

    steps, passed = plan(policy(table=table), "c", "diagnosis", ("gemini",), ("gemini",), (QWEN,))

    assert names(steps) == ["gemini", "local"] and passed == ("anthropic (not declared)",)


def test_an_engine_named_twice_is_asked_once():
    table = {"diagnosis": (Preference("gemini", "a"), Preference("gemini", "b"), Preference("local", "c"))}

    steps, _ = plan(policy(table=table), "c", "diagnosis", ALL, ALL, (QWEN,))

    assert names(steps) == ["gemini", "local"]


def test_the_route_says_the_class_the_kind_the_choice_and_what_was_left_out():
    route = route_of("external_allowed", "diagnosis", Step("openai", "second opinion"), (("anthropic", "status 429"),), ("gemini (key not set)",))

    assert route == "external_allowed; kind=diagnosis; chose openai: second opinion; silent: anthropic (status 429); passed over: gemini (key not set)"
    assert route_of("internal_only", "", None, (), ()) == "internal_only"
