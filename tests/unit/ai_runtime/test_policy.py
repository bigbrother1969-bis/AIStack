from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from aistack.ai_runtime import call_journal, policy
from aistack.ai_runtime.policy import AIPolicy, load_ai_policy
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer


def declared(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ai_policy.yml"
    path.write_text(text, encoding="utf-8")
    return path


def answer(**changes) -> AIRuntimeAnswer:
    base = AIRuntimeAnswer(
        operation="reason", subject="host.disk", model="qwen2.5:7b", prompt="p", response="r", reachable=True
    )
    return replace(base, **changes)


def test_the_shipped_policy_keeps_every_use_inside():
    shipped = load_ai_policy(policy.SHIPPED)

    assert shipped.callers
    assert all(declared == policy.INTERNAL_ONLY for declared in shipped.callers.values())
    assert not shipped.allows_external("troubleshooting")


def test_a_caller_the_file_does_not_name_is_internal():
    assert AIPolicy().class_of("someone.new") == policy.INTERNAL_ONLY
    assert not AIPolicy().allows_external("someone.new")


def test_a_caller_declared_external_allowed_may_go_outside(tmp_path):
    path = declared(tmp_path, "callers:\n  troubleshooting: external_allowed\n")

    loaded = load_ai_policy(path)

    assert loaded.allows_external("troubleshooting")
    assert not loaded.allows_external("security.page")


@pytest.mark.parametrize(
    "text, words",
    [
        ("callers:\n  troubleshooting: sometimes\n", "unknown class"),
        ("callers: [a, b]\n", "mapping"),
        ("default_class: external_allowed\n", "unknown key"),
        ("internal_hosts: nas\n", "list of host names"),
        ("- just a list\n", "mapping"),
    ],
)
def test_a_mistyped_policy_is_refused_with_its_words(tmp_path, text, words):
    with pytest.raises(ValueError, match=words):
        load_ai_policy(declared(tmp_path, text))


def test_an_empty_policy_is_the_cautious_one(tmp_path):
    assert load_ai_policy(declared(tmp_path, "")) == AIPolicy()


@pytest.mark.parametrize(
    "host, kind",
    [
        ("127.0.0.1", "internal"),
        ("::1", "internal"),
        ("192.168.1.10", "internal"),
        ("10.0.0.5", "internal"),
        ("8.8.8.8", "external"),
        ("api.example.com", "external"),
    ],
)
def test_an_engine_is_internal_on_the_loopback_or_the_lan(host, kind):
    assert AIPolicy().kind_of_host(host) == kind


def test_a_host_name_the_owner_lists_is_internal():
    assert AIPolicy(internal_hosts=("msi.lan",)).kind_of_host("msi.lan") == "internal"


def test_an_unreadable_policy_gives_the_cautious_one(monkeypatch, tmp_path):
    monkeypatch.setattr(policy, "configured", lambda shipped: tmp_path / "missing.yml")

    assert policy.current_policy() == policy.CAUTIOUS


def test_the_journal_says_what_a_routing_by_policy_would_have_changed(tmp_path):
    internal = AIPolicy(callers={"troubleshooting": policy.INTERNAL_ONLY})
    allowed = AIPolicy(callers={"troubleshooting": policy.EXTERNAL_ALLOWED})

    outside = call_journal.call_of("troubleshooting", answer(external=True), 1.0, policy=internal)
    permitted = call_journal.call_of("troubleshooting", answer(external=True), 1.0, policy=allowed)
    local = call_journal.call_of("troubleshooting", answer(), 1.0, policy=internal)

    assert (outside.policy_class, outside.policy_differs) == ("internal_only", True)
    assert (permitted.policy_class, permitted.policy_differs) == ("external_allowed", False)
    assert (local.policy_class, local.policy_differs) == ("internal_only", False)


def test_the_class_and_the_difference_come_back_from_the_journal(tmp_path):
    call_journal.append(
        tmp_path, call_journal.call_of("troubleshooting", answer(external=True), 1.0, policy=AIPolicy())
    )

    (line,) = call_journal.read(tmp_path)

    assert (line.policy_class, line.policy_differs) == ("internal_only", True)


def test_a_line_written_before_the_policy_still_reads(tmp_path):
    (tmp_path / call_journal.JOURNAL_FILE).write_text(
        '{"at": "2026-11-21T07:27:12+00:00", "caller": "security.page", "operation": "reason", "language": "fr",'
        ' "answered_by": "qwen2.5:7b", "reached_external": false, "reachable": true, "seconds": 1.0, "set_aside": ""}\n',
        encoding="utf-8",
    )

    (line,) = call_journal.read(tmp_path)

    assert (line.policy_class, line.policy_differs) == ("", False)


def test_the_shipped_policy_gives_each_operation_a_kind_and_each_kind_its_engines_with_a_reason():
    shipped = load_ai_policy(policy.SHIPPED)

    for operation in ("reason", "explain", "recommend"):
        kind = shipped.kind_of("troubleshooting", operation)
        assert kind and shipped.preferred(kind), operation
        assert all(line.why for line in shipped.preferred(kind))
        assert shipped.preferred(kind)[-1].engine == "local"


def test_a_caller_and_operation_kind_wins_over_the_operation_kind(tmp_path: Path):
    loaded = load_ai_policy(declared(tmp_path, "kinds:\n  reason: diagnosis\n  security.page.reason: security\n"))

    assert loaded.kind_of("troubleshooting", "reason") == "diagnosis"
    assert loaded.kind_of("security.page", "reason") == "security"
    assert loaded.kind_of("security.page", "explain") == ""
    assert loaded.kind_of("x", "compare") == ""


def test_the_table_loads_in_order_with_its_reasons(tmp_path: Path):
    loaded = load_ai_policy(declared(tmp_path, "preferences:\n  diagnosis:\n    - {engine: openai, why: a}\n    - {engine: local, why: b}\n"))

    assert [(line.engine, line.why) for line in loaded.preferred("diagnosis")] == [("openai", "a"), ("local", "b")]
    assert loaded.preferred("nothing") == ()


@pytest.mark.parametrize(
    "text",
    [
        "kinds: [reason]\n",
        "kinds:\n  reason: ''\n",
        "preferences: [a]\n",
        "preferences:\n  diagnosis: openai\n",
        "preferences:\n  diagnosis:\n    - {engine: openai}\n",
        "preferences:\n  diagnosis:\n    - {engine: '', why: a}\n",
    ],
)
def test_a_badly_declared_kind_or_table_is_refused(tmp_path: Path, text: str):
    with pytest.raises(ValueError):
        load_ai_policy(declared(tmp_path, text))


def test_the_journal_keeps_the_kind_and_nothing_else_of_the_choice(tmp_path: Path):
    line = call_journal.call_of("troubleshooting", answer(kind="diagnosis", route="external_allowed; kind=diagnosis"), 1.0)
    call_journal.append(tmp_path, line)

    assert call_journal.read(tmp_path)[0].kind == "diagnosis"
