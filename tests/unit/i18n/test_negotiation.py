from aistack.i18n import (
    LANGUAGE_COOKIE,
    Language,
    Languages,
    language_cookie_header,
    negotiate_language,
    read_cookie,
    with_language,
)

LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


# --------------------------------------------------------------------
# negotiate_language — requested, then remembered, then reference
# --------------------------------------------------------------------


def test_a_requested_language_wins_and_is_remembered():
    choice = negotiate_language("en", "fr", LANGUAGES)

    assert choice.lang == "en"
    assert choice.remember is True


def test_a_remembered_language_is_used_without_being_rewritten():
    choice = negotiate_language(None, "en", LANGUAGES)

    assert choice.lang == "en"
    assert choice.remember is False


def test_nothing_chosen_serves_the_reference():
    choice = negotiate_language(None, None, LANGUAGES)

    assert choice.lang == "fr"
    assert choice.remember is False


def test_an_unknown_requested_language_falls_through_to_the_cookie():
    choice = negotiate_language("xx", "en", LANGUAGES)

    assert choice.lang == "en"
    assert choice.remember is False


def test_a_stale_cookie_falls_through_to_the_reference():
    assert negotiate_language(None, "de", LANGUAGES).lang == "fr"


# --------------------------------------------------------------------
# The cookie itself
# --------------------------------------------------------------------


def test_the_cookie_header_remembers_the_language_for_the_whole_site():
    header = language_cookie_header("en")

    assert header.startswith(f"{LANGUAGE_COOKIE}=en;")
    assert "Path=/" in header
    assert "SameSite=Lax" in header


def test_read_cookie_finds_the_language_among_other_cookies():
    header = 'other="a;b"; aistack_lang=en; session=xyz'

    assert read_cookie("session=xyz; aistack_lang=en") == "en"
    assert read_cookie(header) == "en"


def test_read_cookie_reports_an_absent_cookie_as_none():
    assert read_cookie(None) is None
    assert read_cookie("") is None
    assert read_cookie("session=xyz") is None
    assert read_cookie("aistack_lang=") is None


# --------------------------------------------------------------------
# with_language — the language travels in the link to another host
# --------------------------------------------------------------------


def test_with_language_appends_a_query_string():
    assert with_language("http://GIGABYTE:8181", "en") == "http://GIGABYTE:8181?lang=en"


def test_with_language_extends_an_existing_query_string():
    assert with_language("/health.html?x=1", "fr") == "/health.html?x=1&lang=fr"


def test_with_language_keeps_the_fragment_last():
    assert with_language("/architecture.html#dependencies", "en") == (
        "/architecture.html?lang=en#dependencies"
    )


def test_with_language_leaves_an_in_page_anchor_alone():
    assert with_language("#top", "en") == "#top"
