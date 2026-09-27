import pytest

from aistack.i18n import Translator, default_languages, translator_for


def translator(lang: str = "en") -> Translator:
    return Translator(
        lang=lang,
        reference="fr",
        messages={"a.title": "Health", "a.count": "{measured}/{total} measured"},
        reference_messages={
            "a.title": "Santé",
            "a.count": "{measured}/{total} mesurés",
            "a.only_in_reference": "Seulement en français",
        },
    )


def test_a_message_is_returned_in_the_translators_language():
    assert translator()("a.title") == "Health"


def test_named_placeholders_are_filled():
    assert translator()("a.count", measured=4, total=5) == "4/5 measured"


def test_a_message_missing_from_the_language_falls_back_to_the_reference():
    assert translator()("a.only_in_reference") == "Seulement en français"


def test_a_message_missing_everywhere_is_a_stated_defect():
    with pytest.raises(KeyError, match=r"no message 'a\.nowhere'"):
        translator()("a.nowhere")


def test_has_reports_whether_a_key_can_be_answered():
    assert translator().has("a.only_in_reference")
    assert not translator().has("a.nowhere")


def test_the_real_translator_serves_each_declared_language():
    for code in default_languages().codes():
        assert translator_for(code).lang == code


def test_an_unknown_language_gets_the_reference_not_an_error():
    reference = default_languages().reference

    assert translator_for("xx").lang == reference
    assert translator_for(None).lang == reference
