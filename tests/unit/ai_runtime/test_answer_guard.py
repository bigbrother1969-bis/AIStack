from __future__ import annotations

import pytest

from aistack.ai_runtime import answer_guard as guard

CALM = "Cela peut être normal. Tu peux lancer `ls -la /etc/nut` puis `systemctl status nut-server`."


def test_a_calm_tutoiement_with_two_read_only_commands_breaks_no_rule():
    assert guard.problems(CALM, "fr") == ()


@pytest.mark.parametrize(
    "text, rule",
    [
        ("Ces changements pourraient indiquer une tentative de compromission.", "alarming wording"),
        ("Cela pourrait être une tentative d'attaque.", "alarming wording"),
        ("Une tentative de modification non autorisée.", "alarming wording"),
        ("Ce fichier n'est pas normal.", "alarming wording"),
        ("Un fichier malveillant.", "alarmist wording"),
        ("Vous devriez vérifier.", "vouvoiement"),
        ("Exécutez `ls -la`.", "vouvoiement"),
        ("Dis-le à ton owner.", "the word owner"),
        ("Lance `systemctl restart nut-server`.", "a command that changes something"),
        ("Lance `a b`, `c d`, `e f` et `g h`.", "more than 3 commands"),
    ],
)
def test_each_rule_the_engine_is_given_is_checked_in_code(text, rule):
    assert rule in guard.problems(text, "fr")


def test_a_path_or_a_single_word_in_backticks_is_not_a_command():
    text = "Regarde `/etc/nut/upsd.conf`, `/etc/ufw/user.rules`, `cloudflared` et `/usr/local/sbin`, puis `ls -l` ."

    assert guard.commands_in(text) == ["ls -l"]
    assert guard.problems(text, "fr") == ()


def test_sudo_does_not_hide_the_program_and_three_commands_are_allowed():
    text = "`sudo journalctl -u x`, `ls -l /a`, `cat /b`"

    assert len(guard.commands_in(text)) == 3 and guard.problems(text, "fr") == ()


def test_vouvoiement_is_a_rule_of_the_french_page_only():
    assert guard.problems("You can run `ls -la`.", "en") == ()
    assert guard.problems("Vous pouvez.", "en") == ()


class _Inner:
    def __init__(self, text: str, reason: str = "") -> None:
        self.text, self.reason = text, reason

    def complete(self, prompt: str) -> tuple[str, str]:
        return self.text, self.reason


def test_a_guarded_engine_sets_aside_an_answer_that_breaks_a_rule_and_says_which():
    text, reason = guard.GuardedEngine(_Inner("Une tentative de compromission."), "fr", "Olala").complete("p")

    assert text == "" and reason.startswith("Olala answer set aside") and "alarming wording" in reason


def test_a_guarded_engine_passes_a_good_answer_and_an_empty_one_unchanged():
    assert guard.GuardedEngine(_Inner(CALM), "fr", "Olala").complete("p") == (CALM, "")
    assert guard.GuardedEngine(_Inner("", "down"), "fr", "Olala").complete("p") == ("", "down")
