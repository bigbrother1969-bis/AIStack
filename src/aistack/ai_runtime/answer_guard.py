"""
What an answer must not say before the page shows it (ADR-0028, slice T4b).

The rules given to a small model in its prompt are followed most of the time, not always: on
20 Nov. 2026 Olala still wrote "tentative de compromission" and gave five commands where three
were asked. The rules are therefore also checked in code. An answer that breaks one is not shown;
it is asked once more with the rules recalled, then handed to the next declared engine, as an answer cut at the token limit is.

Pure: text in, the names of the rules broken out.
"""

from __future__ import annotations

import re

from aistack.ai_runtime.engine import AIEngine

MAX_COMMANDS = 3

# « vous » and the forms of the verbs a model writes to a reader it does not tutoie.
VOUS = re.compile(
    r"\b(vous|votre|vos|exécutez|examinez|vérifiez|consultez|lancez|regardez|considérez|utilisez|tapez|ouvrez"
    r"|affichez|listez|lisez|contrôlez|pouvez|devez|avez|êtes|rappelez-vous|veuillez|suivez|essayez|notez)\b",
    re.IGNORECASE,
)
OWNER = re.compile(r"\bowner\b", re.IGNORECASE)
ALARMIST = re.compile(
    r"\b(inquiétant|inquiétante|alarmant|alarmante|attaquant|malveillant|malveillante|pirate|piraté)\b", re.IGNORECASE
)
# The words the engine rules forbid: the alarm is for the reader to raise once he has checked.
FORBIDDEN_PHRASES = re.compile(
    r"\btentative\s+d(?:e|['’])\s*\w+|\bn['’]est\s+pas\s+normale?\b|\bnot\s+normal\b|\battack\s+attempt\b",
    re.IGNORECASE,
)
CHANGING = re.compile(
    r"(\brm\s+-|\brm\s+/|\bsystemctl\s+(stop|start|restart|reload|enable|disable|mask|kill)\b"
    r"|\bdocker\s+(rm|stop|kill|restart|run|exec|rmi|compose\s+(down|up|restart|rm))\b|\b(kill|pkill|killall)\s"
    r"|\bchmod\b|\bchown\b|\biptables\b|\bufw\s+(allow|deny|delete|enable|disable|reject|insert)\b"
    r"|\bapt(-get)?\s+(remove|purge|install|upgrade|dist-upgrade|autoremove)\b|\breboot\b|\bshutdown\b|\bmkfs\b"
    r"|\bdd\s+if=|\bsed\s+-i\b|\btee\s|\bmv\s|\bcp\s|\btruncate\b|\bpasswd\b|\buserdel\b|>\s*/)"
)
CODE = re.compile(r"`([^`\n]+)`")
_PROGRAM = re.compile(r"^[a-z][a-z0-9_-]*$")


def outside_code(text: str) -> str:
    """Lines that look like a shell prompt, for commands not put in backticks."""

    return "\n".join(line for line in text.splitlines() if line.lstrip().startswith(("$ ", "# ", "sudo ")))


def commands_in(text: str) -> list[str]:
    """The backticked spans that are commands: several words, the first one a program, not a path."""

    found = []
    for span in CODE.findall(text):
        words = span.split()
        program = words[1] if len(words) > 1 and words[0] == "sudo" else words[0]
        if len(words) > 1 and _PROGRAM.match(program):
            found.append(span)
    return found


def problems(text: str, language: str) -> tuple[str, ...]:
    """The rules this answer breaks; empty when it can be shown."""

    broken: list[str] = []
    if FORBIDDEN_PHRASES.search(text):
        broken.append("alarming wording")
    elif ALARMIST.search(text):
        broken.append("alarmist wording")
    if language == "fr" and VOUS.search(text):
        broken.append("vouvoiement")
    if OWNER.search(text):
        broken.append("the word owner")
    if any(CHANGING.search(span) for span in CODE.findall(text)) or CHANGING.search(outside_code(text)):
        broken.append("a command that changes something")
    if len(commands_in(text)) > MAX_COMMANDS:
        broken.append(f"more than {MAX_COMMANDS} commands")
    return tuple(broken)


REMINDER = {
    "fr": "\n\nTa réponse précédente a été écartée : elle enfreint ces règles ({rules}). Réponds de nouveau, plus court, en les respectant.",
    "en": "\n\nYour previous answer was set aside: it breaks these rules ({rules}). Answer again, shorter, and follow them.",
}
RULE_WORDS = {
    "fr": {
        "alarming wording": "formule alarmante interdite",
        "alarmist wording": "ton alarmiste",
        "vouvoiement": "vouvoiement : tutoie",
        "the word owner": "le mot owner : dis « toi »",
        "a command that changes something": "commande qui modifie quelque chose : lecture seule seulement",
        f"more than {MAX_COMMANDS} commands": f"plus de {MAX_COMMANDS} commandes : {MAX_COMMANDS} au plus",
    },
    "en": {
        "alarming wording": "forbidden alarming wording",
        "alarmist wording": "alarmist tone",
        "vouvoiement": "formal address",
        "the word owner": "the word owner: say 'you'",
        "a command that changes something": "a command that changes something: read-only only",
        f"more than {MAX_COMMANDS} commands": f"more than {MAX_COMMANDS} commands: {MAX_COMMANDS} at most",
    },
}


def reminder(broken: tuple[str, ...], language: str) -> str:
    """The sentence added to the question for the second try: the rules the first answer broke, in the reader's language."""

    code = "fr" if language == "fr" else "en"
    words = RULE_WORDS[code]
    return REMINDER[code].format(rules="; ".join(words.get(rule, rule) for rule in broken))


class GuardedEngine:
    """
    An engine whose answer is set aside, with the rules it broke as the reason, when it breaks one.

    The engine is asked a second time first, with the rules it broke recalled after the question: a
    second try of an engine already running costs seconds, handing the question on may start another
    engine. Only the second answer's breaking of a rule sets it aside.
    """

    def __init__(self, inner: AIEngine, language: str, label: str) -> None:
        self.inner = inner
        self.language = language
        self.label = label

    def complete(self, prompt: str) -> tuple[str, str]:
        text, reason = self.inner.complete(prompt)
        if not text.strip():
            return text, reason
        broken = problems(text, self.language)
        if not broken:
            return text, reason
        text, reason = self.inner.complete(prompt + reminder(broken, self.language))
        if not text.strip():
            return text, reason
        broken = problems(text, self.language)
        if broken:
            return "", f"{self.label} answer set aside twice, it broke the rules: {', '.join(broken)}"
        return text, reason
