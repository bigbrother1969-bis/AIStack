"""The screen for personal data in a question (portal.chat, ADR-0029 § 5 and § 12): kinds found, never the text."""

from __future__ import annotations

import pytest

from aistack.portal.personal_data import screen


def kinds(text: str) -> tuple[str, ...]:
    return screen(text).kinds


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("écris à marie.durand@example.org", ("email",)),
        ("mon numéro est le 06 12 34 56 78", ("phone", "identity")),
        ("appelle le +33 6 12 34 56 78", ("phone",)),
        ("vire sur FR76 3000 6000 0112 3456 7890 189", ("iban",)),
        ("carte 4111 1111 1111 1111", ("card",)),
        ("sécu 1 85 05 78 006 084 36", ("social_security",)),
        ("j'habite 12 rue des Lilas", ("address",)),
        ("c'est au 75011 Paris", ("address",)),
        ("le serveur est en 192.168.1.10", ("network",)),
        ("la carte 8c:97:ea:31:3c:1d ne répond pas", ("network",)),
        ("ma clé est AIzaSyA1234567890abcdefghijklmnopqrstu", ("secret",)),
        ("-----BEGIN OPENSSH PRIVATE KEY-----", ("secret",)),
        ("né le 12/03/1985", ("birth",)),
        ("mon mot de passe ne marche plus", ("secret",)),
        ("ma femme a rendez-vous chez le médecin", ("family", "health")),
        ("je veux contester mon impôt, il faut un avocat", ("legal",)),
        ("mon fils est malade depuis hier", ("family", "health")),
        ("j'ai de la fièvre et une douleur au dos", ("health",)),
        ("quels sont les symptômes d'une allergie", ("health",)),
        ("je suis enceinte de trois mois", ("health",)),
        ("comment lire ma fiche de paie", ("money",)),
        ("je viens de recevoir une amende", ("legal",)),
        ("mon casier judiciaire est-il consultable", ("legal",)),
        ("comment fonctionne mon empreinte digitale sur le portable", ("biometric",)),
        ("ma religion m'interdit de travailler le samedi", ("belief",)),
        ("mon employeur m'a envoyé un avertissement", ("work",)),
        ("comment partager ma localisation avec ma conjointe", ("place", "family")),
        ("où est mon passeport, il me faut un visa", ("identity",)),
        ("what is my health insurance, my wife asks", ("family", "health")),
    ],
)
def test_what_is_personal_is_found_by_kind(text, expected):
    found = kinds(text)

    for kind in expected:
        assert kind in found, (text, found)


@pytest.mark.parametrize(
    "text",
    [
        "comment régler la luminosité de l'écran ?",
        "quelle est l'empreinte carbone de l'IA en France ?",
        "comment retrouver un fichier supprimé dans la corbeille",
        "pourquoi mon navigateur est lent",
        "le chiffre 9234567890123 est-il premier",
        "version 2.1.0 du logiciel",
        "explique la différence entre RAM et disque",
    ],
)
def test_an_everyday_question_holds_nothing_personal(text):
    assert kinds(text) == (), text


@pytest.mark.parametrize(
    "text",
    [
        "comment brancher une enceinte connectée au salon",
        "la tension du réseau est instable",
        "comment configurer une imprimante réseau",
        "où ranger le passeport de la carte mère dans le boîtier",
    ],
)
def test_an_everyday_word_that_looks_private_is_not_taken_for_it(text):
    assert kinds(text) == (), text


def test_every_kind_the_screen_can_return_has_a_label_in_both_languages():
    from pathlib import Path

    import yaml

    from aistack.portal.personal_data import SHAPES, WORD_KINDS

    root = Path(__file__).parents[3] / "src" / "aistack" / "i18n" / "catalogs"

    for lang in ("fr", "en"):
        labels = yaml.safe_load((root / lang / "ask.yml").read_text(encoding="utf-8"))["personal"]

        for kind in (*SHAPES, *WORD_KINDS):
            assert labels.get(kind), (lang, kind)


def test_a_number_that_is_not_a_card_or_an_iban_is_not_taken_for_one():
    assert "card" not in kinds("le numéro 4111 1111 1111 1112 est faux")
    assert "iban" not in kinds("FR76 3000 6000 0112 3456 7890 180")


def test_words_are_whole_and_accents_and_case_do_not_matter():
    assert "health" in kinds("MEDECIN")
    assert "health" in kinds("j'ai vu un médecin")
    assert "health" not in kinds("le médecinal")
    assert "family" in kinds("MAMIE adore les photos")


def test_the_screen_returns_kinds_never_the_text():
    found = screen("écris à marie.durand@example.org")

    assert found.found and found.kinds == ("email",)
    assert "marie" not in repr(found)


def test_the_kinds_come_in_a_stable_order():
    assert kinds("mon fils, jean@example.org, 06 12 34 56 78") == ("email", "phone", "family")


def test_in_doubt_a_number_shaped_like_a_social_security_number_is_kept_inside():
    assert "social_security" in kinds("le chiffre 1234567890123 est-il premier")
