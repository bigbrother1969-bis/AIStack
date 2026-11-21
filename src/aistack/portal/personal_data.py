"""
Is there personal data in a question? (`portal.chat`, ADR-0029 § 5 and § 12)

A deterministic screen, run on the question before any engine is chosen. It returns the *kinds* it found
(`email`, `phone`...), never the text it found them in: the kinds are what the page and the journal may
say. In doubt the answer is "found": a question that is kept inside by mistake costs a weaker answer, a
question that leaves by mistake cannot be called back.

What it recognises is of two sorts. Shapes, by their form (this module); and words that point at a
private matter, declared in `portal/definitions/personal_data.yml`. A name alone is neither: it is
caught only through those words or another sign. The limit is the page's own and is written there.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from aistack.config import configured

DEFINITION = Path(__file__).resolve().parent / "definitions" / "personal_data.yml"

EMAIL = "email"
PHONE = "phone"
IBAN = "iban"
CARD = "card"
SOCIAL_SECURITY = "social_security"
ADDRESS = "address"
NETWORK = "network"
SECRET = "secret"
BIRTH = "birth"

# The order the kinds are listed in, for a stable text.
SHAPES = (EMAIL, PHONE, IBAN, CARD, SOCIAL_SECURITY, ADDRESS, NETWORK, SECRET, BIRTH)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\d.])(?:(?:\+|00)\s?\d{1,3}[\s.-]?|0)[1-9](?:[\s.-]?\d{2}){4}(?![\d])|(?<!\d)\+\d{8,15}(?!\d)")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")
_DIGITS = re.compile(r"(?<![\d])(?:\d[ -]?){12,18}\d(?![\d])")
_SOCIAL = re.compile(r"(?<!\d)[12][ .]?\d{2}[ .]?(?:0[1-9]|1[0-2]|[2-9]\d)[ .]?(?:\d{2}|2[AB])[ .]?\d{3}[ .]?\d{3}(?:[ .]?\d{2})?(?!\d)", re.I)
_STREET = re.compile(
    r"\b\d{1,4}\s*(?:bis|ter)?\s*,?\s*(?:rue|avenue|av\.|boulevard|bd|chemin|impasse|allée|allee|route|place|quai|cours|square|cité|rond-point)\b",
    re.I,
)
_POSTCODE = re.compile(r"(?<!\d)(?:0[1-9]|[1-8]\d|9[0-5]|97\d|98\d)\d{3}\s+[A-ZÉÈÊÀÂÎÔÛÇ][\wÀ-ÿ'-]+")
_IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_SECRET_FORM = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{16,}|\bAIza[0-9A-Za-z_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{20,}"
    r"|\bxox[abp]-[A-Za-z0-9-]{10,}|(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/_-]{40,}(?![A-Za-z0-9+/=_-])"
)
_BIRTH = re.compile(
    r"\b(?:née?|naissance|born)\b[^.\n]{0,25}?\b\d{1,2}[/.-]\d{1,2}[/.-](?:\d{2}|\d{4})\b"
    r"|\b(?:née?|naissance|born)\b[^.\n]{0,25}?\b\d{1,2}\s+(?:janv|févr|fevr|mars|avr|mai|juin|juil|août|aout|sept|oct|nov|déc|dec)",
    re.I,
)


def _luhn(digits: str) -> bool:
    total = 0

    for index, char in enumerate(reversed(digits)):
        value = int(char)

        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9

        total += value

    return total % 10 == 0


def _iban_valid(text: str) -> bool:
    compact = text.replace(" ", "").upper()

    if not 15 <= len(compact) <= 34:
        return False

    moved = compact[4:] + compact[:4]
    number = "".join(str(int(char, 36)) for char in moved)

    return int(number) % 97 == 1


def _card_found(text: str) -> bool:
    for found in _DIGITS.finditer(text):
        digits = re.sub(r"\D", "", found.group())

        if 13 <= len(digits) <= 19 and _luhn(digits):
            return True

    return False


def _folded(text: str) -> str:
    """Lower case, accents removed, apostrophes and dashes made spaces: words compared on their letters."""

    plain = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))

    return " " + re.sub(r"[^a-z0-9]+", " ", plain).strip() + " "


def load_personal_data_yaml(path: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """
    The words of `personal_data.yml` as `(kind, folded words)`; a `ValueError` names what is wrong. Read for
    each question (a small file), so an edit of the owner's copy counts at once.
    """

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("cues")

    if not isinstance(raw, dict):
        raise ValueError(f"{path}: cues must be a mapping of a kind to its words")

    found = []

    for kind, words in raw.items():
        if not isinstance(kind, str) or not isinstance(words, list) or not all(isinstance(w, str) and w.strip() for w in words):
            raise ValueError(f"{path}: cues {kind!r} must be a list of words")

        found.append((kind, tuple(_folded(word) for word in words)))

    return tuple(found)


@dataclass(frozen=True)
class Screen:
    """What the screen found: the kinds, in a stable order. Never the text."""

    kinds: tuple[str, ...]

    @property
    def found(self) -> bool:
        return bool(self.kinds)


def screen(text: str, definition: Path | None = None) -> Screen:
    """The kinds of personal data in `text`; empty when none is recognised."""

    kinds: list[str] = []

    def add(kind: str) -> None:
        if kind not in kinds:
            kinds.append(kind)

    if _EMAIL.search(text):
        add(EMAIL)
    if _PHONE.search(text):
        add(PHONE)
    if any(_iban_valid(found.group()) for found in _IBAN.finditer(text)):
        add(IBAN)
    if _card_found(text):
        add(CARD)
    if _SOCIAL.search(text):
        add(SOCIAL_SECURITY)
    if _STREET.search(text) or _POSTCODE.search(text):
        add(ADDRESS)
    if _IPV4.search(text) or _MAC.search(text):
        add(NETWORK)
    if _SECRET_FORM.search(text):
        add(SECRET)
    if _BIRTH.search(text):
        add(BIRTH)

    folded = _folded(text)

    for kind, words in load_personal_data_yaml(definition or configured(DEFINITION)):
        if any(word in folded for word in words):
            add(kind)

    order = {name: index for index, name in enumerate((*SHAPES, "identity", "secret", "family", "health", "money", "legal"))}

    return Screen(tuple(sorted(kinds, key=lambda name: order.get(name, 99))))
