"""What a console card's screen asks of the AI engines, from the policy (ADR-0029 § 11)."""

from __future__ import annotations

from pathlib import Path

import aistack
from aistack.ai_runtime.policy import AIPolicy
from aistack.console.ai_use import ai_use_of
from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.console_link import AI_EXTERNAL, AI_LOCAL, AI_NONE
from aistack.contracts.instance_config import InstanceConfig

SHIPPED = Path(aistack.__file__).parent / "console" / "definitions" / "console_links.yml"
INSTANCE = InstanceConfig(lan_hostname="msi", service_ports={"web_lan": 8186, "selection_ui": 8181, "priority_ui": 8182})
POLICY = AIPolicy(callers={"troubleshooting": "external_allowed", "security.page": "internal_only"})


def test_a_screen_that_reaches_no_use_of_a_model_asks_no_engine():
    assert ai_use_of((), POLICY) == AI_NONE


def test_a_screen_that_does_not_declare_its_uses_says_nothing():
    assert ai_use_of(None, POLICY) == ""


def test_an_internal_only_use_stays_on_the_local_engines():
    assert ai_use_of(("security.page",), POLICY) == AI_LOCAL


def test_one_use_that_may_go_outside_makes_the_card_external():
    assert ai_use_of(("security.page", "troubleshooting"), POLICY) == AI_EXTERNAL


def test_a_use_the_policy_does_not_name_is_internal():
    assert ai_use_of(("somebody.new",), POLICY) == AI_LOCAL


def test_the_line_follows_the_policy_when_the_owner_changes_it():
    stricter = AIPolicy(callers={"troubleshooting": "internal_only"})

    assert ai_use_of(("troubleshooting",), stricter) == AI_LOCAL


def test_every_shipped_card_declares_the_uses_of_a_model_its_screen_reaches():
    import yaml

    cards = yaml.safe_load(SHIPPED.read_text(encoding="utf-8"))["links"]

    assert cards and all("ai_callers" in card for card in cards)


def test_the_shipped_cards_say_which_screens_use_the_engines():
    links = load_console_links_yaml(SHIPPED, lang="fr", instance=INSTANCE, policy=POLICY)
    uses = {link.name: link.ai_use for link in links}

    assert uses["Assistant de pannes"] == AI_EXTERNAL
    assert uses["Cockpit Santé"] == AI_EXTERNAL
    assert uses["Sécurité"] == AI_LOCAL
    assert uses["Moteurs IA"] == AI_NONE
    assert uses["Selection UI"] == AI_NONE
    assert all(use for use in uses.values())


def test_a_card_the_owner_adds_without_ai_callers_says_nothing(tmp_path: Path):
    copy = tmp_path / "console_links.yml"
    copy.write_text(
        "links:\n  - name: Nextcloud\n    description: Les fichiers\n    url: https://cloud.example.org\n    scope: public\n",
        encoding="utf-8",
    )

    (link,) = load_console_links_yaml(copy, instance=INSTANCE, policy=POLICY)

    assert link.ai_callers is None and link.ai_use == ""


def test_a_mistyped_ai_callers_is_refused_with_its_words(tmp_path: Path):
    import pytest

    copy = tmp_path / "console_links.yml"
    copy.write_text(
        "links:\n  - name: X\n    description: d\n    url: /x\n    scope: public\n    ai_callers: troubleshooting\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ai_callers must be a list"):
        load_console_links_yaml(copy, instance=INSTANCE)


def test_a_copy_made_before_ai_callers_takes_them_from_the_shipped_card(tmp_path: Path):
    shipped = SHIPPED
    copy = tmp_path / "console_links.yml"
    copy.write_text(
        "links:\n"
        "  - name: Mon assistant\n    description: Texte à moi\n    service: web_lan\n    path: /troubleshooting/\n    scope: lan\n"
        "  - name: Mon service\n    description: A moi\n    url: https://cloud.example.org\n    scope: public\n",
        encoding="utf-8",
    )

    links = load_console_links_yaml(copy, lang="fr", instance=INSTANCE, completing=shipped, policy=POLICY)
    by_name = {link.name: link for link in links}

    assert by_name["Mon assistant"].ai_use == AI_EXTERNAL
    assert by_name["Mon service"].ai_use == ""
    assert by_name["Mon assistant"].description == "Texte à moi"


def test_every_card_that_asks_an_engine_says_so_in_its_own_sentence():
    from aistack.console.yaml.store import load_console_links_yaml
    from aistack.tasks.console_render import SHIPPED_CONSOLE_LINKS

    for link in load_console_links_yaml(SHIPPED_CONSOLE_LINKS):
        if link.ai_callers:
            assert link.ai, f"{link.name} uses an AI engine but has no `ai` sentence"
