"""
Put the local engines side by side on the same findings (`aistack.cli.ai_compare`).

Pure: the engines are asked through a function the caller gives, the clock is
the caller's too. What is checked automatically is only what a reader would
otherwise have to spot by eye (a "vous" where the page says "tu", the word
"owner", a command that changes something); a quality judgement stays the
reader's. Nothing here reads a report or writes a file.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs

from aistack.ai_runtime.definition import LocalEngineDefinition
from aistack.ai_runtime.ollama_engine import DEFAULT_TIMEOUT_SECONDS
from aistack.ai_runtime.openai_chat_engine import REASONING_EFFORTS
from aistack.ai_runtime.yaml.store import ENGINE_KINDS
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.runtime_finding import RuntimeFinding

_SPEC = re.compile(r"^(?P<kind>[a-z_]+)@(?P<host>[^:/\s]+):(?P<port>\d+)/(?P<model>[^?\s]+)(?:\?(?P<query>\S*))?$")
_QUERY_KEYS = ("effort", "label", "timeout")


def parse_engine(spec: str) -> LocalEngineDefinition:
    """`kind@host:port/model[?effort=low&label=Olala&timeout=300]`, as an engine to ask."""

    found = _SPEC.match(spec.strip())
    if found is None:
        raise ValueError(f"engine {spec!r}: expected kind@host:port/model[?effort=..&label=..&timeout=..]")
    kind = found["kind"]
    if kind not in ENGINE_KINDS:
        raise ValueError(f"engine {spec!r}: unknown kind {kind!r} (one of {', '.join(ENGINE_KINDS)})")

    query = parse_qs(found["query"] or "", keep_blank_values=True)
    unknown = [key for key in query if key not in _QUERY_KEYS]
    if unknown:
        raise ValueError(f"engine {spec!r}: unknown option {unknown[0]!r} (one of {', '.join(_QUERY_KEYS)})")
    effort = query.get("effort", [None])[0]
    if effort is not None and effort not in REASONING_EFFORTS:
        raise ValueError(f"engine {spec!r}: unknown effort {effort!r} (one of {', '.join(REASONING_EFFORTS)})")

    return LocalEngineDefinition(
        kind=kind,
        host=found["host"],
        port=int(found["port"]),
        model=found["model"],
        timeout=float(query.get("timeout", [DEFAULT_TIMEOUT_SECONDS])[0]),
        reasoning_effort=effort,
        label=query.get("label", [""])[0],
    )


def name_of(engine: LocalEngineDefinition) -> str:
    base = engine.label or engine.model
    return f"{base} ({engine.reasoning_effort})" if engine.reasoning_effort else base


# ---------------------------------------------------------------------------
# What is checked by machine.
# ---------------------------------------------------------------------------

FLAGS = {
    "empty": "pas de réponse",
    "vous": "vouvoie (la page tutoie)",
    "english": "écrit en anglais",
    "alarmist": "ton alarmiste",
    "owner": "écrit « owner »",
    "changing_command": "cite une commande qui modifie",
    "intrusion": "parle d'intrusion sans la nier",
}

# « vous » and the forms of the verbs a model writes to a reader it does not tutoie.
_VOUS = re.compile(
    r"\b(vous|votre|vos|exécutez|examinez|vérifiez|consultez|lancez|regardez|considérez|utilisez|tapez|ouvrez"
    r"|affichez|listez|lisez|contrôlez|pouvez|devez|avez|êtes|faites|rappelez-vous|veuillez|suivez|essayez|notez)\b",
    re.IGNORECASE,
)
_ENGLISH_WORDS = frozenset(
    "the and of is are to that this with these were was for on in be it as by from you should your".split()
)
_FRENCH_WORDS = frozenset("le la les des du de et est que qui un une sur dans pour au aux ce cette ces par pas".split())
_ALARMIST = re.compile(r"\b(inquiétant|inquiétante|alarmant|alarmante|attaquant|malveillant|malveillante|pirate|piraté)\b", re.IGNORECASE)
_NEGATION = re.compile(r"\b(pas|aucun|aucune|sans|ni|jamais)\b|\bn['’]|\bne\b", re.IGNORECASE)
_OWNER = re.compile(r"\bowner\b", re.IGNORECASE)
_INTRUSION = re.compile(r"\b(intrusion|compromis|compromission|piraté)\b", re.IGNORECASE)
_CHANGING = re.compile(
    r"(\brm\s+-|\brm\s+/|\bsystemctl\s+(stop|start|restart|reload|enable|disable|mask|kill)\b"
    r"|\bdocker\s+(rm|stop|kill|restart|run|exec|rmi|compose\s+(down|up|restart|rm))\b|\b(kill|pkill|killall)\s"
    r"|\bchmod\b|\bchown\b|\biptables\b|\bufw\s+(allow|deny|delete|enable|disable|reject|insert)\b"
    r"|\bapt(-get)?\s+(remove|purge|install|upgrade|dist-upgrade|autoremove)\b|\breboot\b|\bshutdown\b|\bmkfs\b"
    r"|\bdd\s+if=|\bsed\s+-i\b|\btee\s|\bmv\s|\bcp\s|\btruncate\b|\bpasswd\b|\buserdel\b|>\s*/)"
)
_CODE = re.compile(r"`([^`\n]+)`")


def review(text: str, lang: str) -> tuple[str, ...]:
    """The flags an answer earns; empty when it has nothing the reader should be warned of."""

    if not text.strip():
        return ("empty",)
    flags: list[str] = []
    if lang == "fr" and _VOUS.search(text):
        flags.append("vous")
    if _OWNER.search(text):
        flags.append("owner")
    if any(_CHANGING.search(span) for span in _CODE.findall(text)) or _CHANGING.search(_outside_code(text)):
        flags.append("changing_command")
    if lang == "fr" and _is_english(text):
        flags.append("english")
    if _ALARMIST.search(text):
        flags.append("alarmist")
    if any(_INTRUSION.search(sentence) and not _NEGATION.search(sentence) for sentence in _sentences(text)):
        flags.append("intrusion")
    return tuple(flags)


def _sentences(text: str) -> list[str]:
    return [part for part in re.split(r"[.!?\n]+", text) if part.strip()]


def _is_english(text: str) -> bool:
    """More English function words than French ones, enough of them to be sure; code spans are ignored."""

    words = re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", _CODE.sub(" ", text).lower())
    english = sum(1 for word in words if word in _ENGLISH_WORDS)
    french = sum(1 for word in words if word in _FRENCH_WORDS)
    return english >= 4 and english > french


def _outside_code(text: str) -> str:
    """Lines that look like a shell prompt, for commands not put in backticks."""

    return "\n".join(line for line in text.splitlines() if line.lstrip().startswith(("$ ", "# ", "sudo ")))


def commands_cited(text: str) -> int:
    return len(_CODE.findall(text))


# ---------------------------------------------------------------------------
# Asking and reporting.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Subject:
    """One finding as it is put to every engine: what is sent, shown as sent."""

    key: str
    title: str
    context: str
    finding: RuntimeFinding


@dataclass(frozen=True)
class Outcome:
    engine: str
    finding: str
    operation: str
    seconds: float
    reachable: bool
    text: str
    reason: str
    flags: tuple[str, ...]
    commands: int


Ask = Callable[[LocalEngineDefinition, Subject, str], AIRuntimeAnswer]


def run(
    engines: Sequence[LocalEngineDefinition],
    subjects: Sequence[Subject],
    operations: Sequence[str],
    lang: str,
    ask: Ask,
    clock: Callable[[], float],
    progress: Callable[[str], None] = lambda line: None,
) -> list[Outcome]:
    """Each engine answers each operation on each finding, alone: no hand-over, so a silent engine stays silent."""

    outcomes: list[Outcome] = []
    for subject in subjects:
        for engine in engines:
            for operation in operations:
                started = clock()
                answer = ask(engine, subject, operation)
                seconds = clock() - started
                text = answer.response.strip() if answer.reachable else ""
                outcomes.append(
                    Outcome(
                        engine=name_of(engine),
                        finding=subject.key,
                        operation=operation,
                        seconds=seconds,
                        reachable=answer.reachable,
                        text=text,
                        reason="" if answer.reachable else answer.unreachable_reason,
                        flags=review(text, lang),
                        commands=commands_cited(text),
                    )
                )
                progress(f"{subject.key} · {name_of(engine)} · {operation} · {seconds:.1f} s")
    return outcomes


def render_markdown(
    outcomes: Sequence[Outcome],
    subjects: Sequence[Subject],
    engines: Sequence[LocalEngineDefinition],
    lang: str,
    when: datetime,
) -> str:
    names = [name_of(engine) for engine in engines]
    out = [
        f"# Comparaison des moteurs locaux — {when:%Y-%m-%d %H:%M}",
        "",
        f"Langue demandée : {lang}. Chaque moteur répond seul, sans repli. Les contrôles automatiques "
        "ne remplacent pas la lecture : ils signalent seulement un « vous », le mot « owner », une commande "
        "qui modifie, un mot d'intrusion, une réponse vide.",
        "",
        "## Résumé",
        "",
        "| Moteur | Réponses | Temps moyen | Plus long | Réponses signalées | Commandes citées |",
        "|---|---|---|---|---|---|",
    ]
    for name in names:
        mine = [o for o in outcomes if o.engine == name]
        answered = [o for o in mine if o.reachable and o.text]
        times = [o.seconds for o in mine]
        flagged = sum(1 for o in mine if o.flags)
        out.append(
            f"| {name} | {len(answered)}/{len(mine)} | {_mean(times):.1f} s | {max(times, default=0):.1f} s "
            f"| {flagged} | {sum(o.commands for o in mine)} |"
        )

    for subject in subjects:
        out += ["", f"## {subject.key} — {subject.title}", "", "Envoyé aux moteurs, en plus des textes fixes de la fiche :", ""]
        out += ["```text", subject.context, "```"]
        for operation in dict.fromkeys(o.operation for o in outcomes if o.finding == subject.key):
            out += ["", f"### {operation}"]
            for o in (o for o in outcomes if o.finding == subject.key and o.operation == operation):
                flags = ", ".join(FLAGS[flag] for flag in o.flags) or "rien à signaler"
                out += ["", f"**{o.engine}** — {o.seconds:.1f} s — {flags}", ""]
                if o.reachable and o.text:
                    out += [f"> {line}" if line.strip() else ">" for line in o.text.splitlines()]
                else:
                    out.append(f"*Pas de réponse : {o.reason or 'aucun texte'}*")
    return "\n".join(out) + "\n"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
