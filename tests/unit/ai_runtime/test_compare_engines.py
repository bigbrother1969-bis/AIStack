from __future__ import annotations

from datetime import datetime

import pytest

from aistack.ai_runtime import compare
from aistack.ai_runtime.definition import LocalEngineDefinition
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import MatchedLine, RuntimeFinding
from aistack.contracts.runtime_observation import LogEntry


def test_a_spec_gives_the_engine_with_its_options():
    engine = compare.parse_engine("openai_chat@127.0.0.1:18095/olala-mini-7a1b?effort=disabled&label=Olala&timeout=300")

    assert engine == LocalEngineDefinition("openai_chat", "127.0.0.1", 18095, "olala-mini-7a1b", 300.0, "disabled", "Olala")
    assert compare.name_of(engine) == "Olala (disabled)"


def test_a_model_name_keeps_its_colon_and_the_options_are_optional():
    engine = compare.parse_engine("ollama@192.168.1.10:11434/qwen2.5:7b")

    assert (engine.kind, engine.host, engine.port, engine.model, engine.reasoning_effort, engine.label) == ("ollama", "192.168.1.10", 11434, "qwen2.5:7b", None, "")
    assert compare.name_of(engine) == "qwen2.5:7b"


@pytest.mark.parametrize(
    "spec, message",
    [
        ("nonsense", "expected kind@host:port/model"),
        ("grpc@h:1/m", "unknown kind"),
        ("ollama@h:1/m?speed=fast", "unknown option"),
        ("openai_chat@h:1/m?effort=extreme", "unknown effort"),
    ],
)
def test_a_wrong_spec_is_refused_by_name(spec: str, message: str):
    with pytest.raises(ValueError, match=message):
        compare.parse_engine(spec)


def test_a_clean_answer_has_nothing_to_flag():
    text = "Tu peux lire le fichier avec `ls -l /usr/local/sbin` puis `journalctl -u aistack-host-hygiene.timer --since '24 hours ago'`."

    assert compare.review(text, "fr") == ()
    assert compare.commands_cited(text) == 2


@pytest.mark.parametrize(
    "text, flag",
    [
        ("Vous devriez regarder le fichier.", "vous"),
        ("Votre machine a changé.", "vous"),
        ("Voici la suggestion pour l'owner.", "owner"),
        ("Lance `sudo systemctl stop aistack-host-hygiene.timer`.", "changing_command"),
        ("Lance `chmod 600 /etc/shadow`.", "changing_command"),
        ("Voici :\n$ rm -rf /tmp/x", "changing_command"),
        ("C'est le signe d'une intrusion possible.", "intrusion"),
        ("   ", "empty"),
    ],
)
def test_what_a_reader_would_have_to_spot_is_flagged(text: str, flag: str):
    assert flag in compare.review(text, "fr")


def test_vous_is_only_flagged_when_the_page_tutoies():
    assert compare.review("Vous pouvez lire le fichier.", "en") == ()


def finding() -> RuntimeFinding:
    return RuntimeFinding(
        subject="security:k",
        signature="ADR-0028/other",
        interpretation="i",
        remediation="r",
        confidence="watch",
        grounding="test",
        evidence=(MatchedLine(LogEntry(offset=0, text="a line")),),
    )


def answer(text: str, reachable: bool = True, reason: str = "") -> AIRuntimeAnswer:
    return AIRuntimeAnswer(operation="reason", subject="security:k", model="m", prompt="p", response=text, reachable=reachable, unreachable_reason=reason, language="fr")


def test_each_engine_answers_each_operation_alone_and_is_timed():
    quick = LocalEngineDefinition("ollama", "h", 1, "qwen")
    silent = LocalEngineDefinition("openai_chat", "h", 2, "olala", label="Olala")
    subject = compare.Subject("k", "Titre", "contexte envoyé", finding())
    asked: list[tuple[str, str]] = []
    ticks = iter([0.0, 2.0, 2.0, 12.0, 12.0, 13.5, 13.5, 14.0])

    def ask(engine, subject, operation):
        asked.append((compare.name_of(engine), operation))
        if engine is silent:
            return answer("", False, "Olala did not answer within 5 seconds")
        return answer("Tu peux lire `ls -l /x`.")

    lines: list[str] = []
    outcomes = compare.run([quick, silent], [subject], ["reason", "explain"], "fr", ask, lambda: next(ticks), lines.append)

    assert asked == [("qwen", "reason"), ("qwen", "explain"), ("Olala", "reason"), ("Olala", "explain")]
    assert [round(o.seconds, 1) for o in outcomes] == [2.0, 10.0, 1.5, 0.5]
    assert outcomes[0].reachable and outcomes[0].commands == 1 and outcomes[0].flags == ()
    assert not outcomes[2].reachable and outcomes[2].flags == ("empty",) and "did not answer" in outcomes[2].reason
    assert len(lines) == 4 and "k · Olala · explain" in lines[-1]


def test_the_report_puts_the_engines_side_by_side():
    quick = LocalEngineDefinition("ollama", "h", 1, "qwen")
    silent = LocalEngineDefinition("openai_chat", "h", 2, "olala", label="Olala")
    subject = compare.Subject("drift.x", "Un titre", "- gravité: watch\n> ligne lue", finding())
    ticks = iter([0.0, 3.0, 3.0, 4.0])

    def ask(engine, subject, operation):
        return answer("Vous devriez voir `ls`.\nDeuxième ligne.") if engine is quick else answer("", False, "Olala could not be reached: refused")

    outcomes = compare.run([quick, silent], [subject], ["reason"], "fr", ask, lambda: next(ticks))
    text = compare.render_markdown(outcomes, [subject], [quick, silent], "fr", datetime(2026, 11, 20, 16, 30))

    assert "# Comparaison des moteurs locaux — 2026-11-20 16:30" in text
    assert "| qwen | 1/1 | 3.0 s | 3.0 s | 1 | 1 |" in text
    assert "| Olala | 0/1 | 1.0 s | 1.0 s | 1 | 0 |" in text
    assert "## drift.x — Un titre" in text and "> ligne lue" in text
    assert "**qwen** — 3.0 s — vouvoie (la page tutoie)" in text
    assert "> Vous devriez voir `ls`." in text and "> Deuxième ligne." in text
    assert "*Pas de réponse : Olala could not be reached: refused*" in text
