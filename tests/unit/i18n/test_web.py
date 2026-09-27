from aistack.i18n import LANGUAGE_COOKIE, Language, Languages
from aistack.i18n.web import page_language

LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


def test_a_requested_language_gives_its_translator_and_a_cookie():
    page = page_language("en", None, LANGUAGES)

    assert page.lang == "en"
    assert page.t("common.settings.link") == "Settings"
    assert page.cookie is not None
    assert page.cookie.startswith(f"{LANGUAGE_COOKIE}=en;")


def test_a_remembered_language_sets_no_cookie():
    page = page_language(None, "en", LANGUAGES)

    assert page.lang == "en"
    assert page.cookie is None


def test_nothing_chosen_is_the_reference_without_a_cookie():
    page = page_language(None, None, LANGUAGES)

    assert page.lang == "fr"
    assert page.t("common.settings.link") == "Paramètres"
    assert page.cookie is None


def test_the_switch_lists_every_language_and_marks_the_current_one():
    page = page_language("en", None, LANGUAGES)

    assert [(option.code, option.current) for option in page.options] == [
        ("fr", False),
        ("en", True),
    ]
    assert page.options[0].name == "Français"


def test_the_template_context_carries_the_three_names():
    context = page_language("fr", None, LANGUAGES).context()

    assert set(context) == {"lang", "t", "language_options"}
    assert context["lang"] == "fr"


def test_each_option_carries_its_language_flag():
    flagged = Languages(
        reference="fr",
        available=(Language("fr", "Français", flag="data:image/svg+xml;base64,AA=="),),
    )

    page = page_language(None, None, flagged)

    assert page.options[0].flag == "data:image/svg+xml;base64,AA=="
