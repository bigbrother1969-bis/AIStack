"""
`aistack.health.labels` — ADR-0010.

A bucket and a domain name are identifiers the health model compares
and weighs; a page shows a translated label for each. These tests hold
both tables against every value the model can actually produce, so a
sixth domain or a fourth bucket added without a label is caught here
rather than shown untranslated on the English console.
"""

from __future__ import annotations

import re
from pathlib import Path

from aistack.contracts.health_score import BUCKETS
from aistack.health.labels import BUCKET_KEYS, DOMAIN_KEYS, bucket_label, domain_label
from aistack.i18n import default_languages, translator_for

REPO_ROOT = Path(__file__).resolve().parents[3]

# The two commands that build a `HealthCockpit` name each domain
# literally (`HealthDomain(name="Stockage", ...)`); reading their text
# finds every name without running either against a real host.
_DOMAIN_NAME = re.compile(r'HealthDomain\(\s*name="([^"]+)"')


def built_domain_names() -> set[str]:
    names: set[str] = set()

    for command in ("console_render.py", "health_render.py"):
        text = (REPO_ROOT / "src" / "aistack" / "cli" / command).read_text(encoding="utf-8")
        names.update(_DOMAIN_NAME.findall(text))

    return names


def test_every_bucket_has_a_label():
    assert set(BUCKET_KEYS) == set(BUCKETS)


def test_every_domain_the_commands_build_has_a_label():
    names = built_domain_names()

    assert names, "no domain name found — the pattern no longer matches"
    assert names <= set(DOMAIN_KEYS)


def test_every_label_key_exists_in_every_language():
    for code in default_languages().codes():
        t = translator_for(code)

        for key in (*BUCKET_KEYS.values(), *DOMAIN_KEYS.values()):
            assert key in t.messages, (code, key)


def test_the_reference_labels_are_the_identifiers_themselves():
    """In French the page says exactly what it said before localization."""

    t = translator_for("fr")

    for bucket in BUCKETS:
        assert bucket_label(t, bucket) == bucket

    for name in DOMAIN_KEYS:
        assert domain_label(t, name) == name


def test_english_labels_are_translated():
    t = translator_for("en")

    assert bucket_label(t, "à surveiller") == "to watch"
    assert domain_label(t, "Sauvegarde / PRA") == "Backup / DR"


def test_an_unknown_value_is_shown_as_declared():
    t = translator_for("en")

    assert bucket_label(t, "inconnu") == "inconnu"
    assert domain_label(t, "Réseau") == "Réseau"
