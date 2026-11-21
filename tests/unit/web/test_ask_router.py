"""*Poser une question* in AIStack's web application (ADR-0029 § 12): any signed-in person asks, the policy chooses, nothing typed is kept."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from tests.unit.web_signed_in import as_user, signed_in

from aistack.ai_runtime import call_journal
from aistack.ai_runtime.call_journal import PORTAL_CHAT
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.i18n import Language, Languages
from aistack.portal.chat import Destination, Exchanges, decision_of
from aistack.web.app import WebPaths, create_app
from aistack.web.exposure import Listeners

LAN_PORT = 8186
LISTENERS = Listeners(public_port=8183, lan_port=LAN_PORT)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))
SECRET_QUESTION = "comment retrouver la photo supprimee de mamie"


def answered(question, operation, language, personal=()) -> AIRuntimeAnswer:
    assert operation == "ask"
    return AIRuntimeAnswer(
        operation="ask",
        subject="question",
        model="Olala",
        prompt="",
        response="Regarde dans la corbeille.",
        reachable=True,
        language=language,
        route="internal_only; kind=question; chose Olala: stays on your machines",
        kind="question",
    )


def silent(question, operation, language, personal=()) -> AIRuntimeAnswer:
    return AIRuntimeAnswer(
        operation="ask", subject="question", model="", prompt="", response="", reachable=False,
        unreachable_reason="Olala: not reachable", language=language, kind="question",
        route="internal_only; kind=question",
    )


INSIDE = Destination(False, "")


def build(tmp_path: Path, ask=answered, where=INSIDE):
    app = create_app(
        tmp_path, LISTENERS, LANGUAGES, WebPaths(), ask_portal=ask, portal_destination=lambda: where,
        run_in_background=lambda work: work(),
    )
    return app


def client(app, user: bool = False) -> TestClient:
    web = TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False)
    return as_user(web) if user else signed_in(web)


def test_the_page_is_for_every_signed_in_person_and_says_where_the_question_goes(tmp_path: Path):
    page = client(build(tmp_path), user=True).get("/ask/?lang=en")

    assert page.status_code == 200
    assert "Ask a question" in page.text and "stays on the machines of the house" in page.text
    assert 'name="question"' in page.text and "title=" in page.text


def test_the_page_names_the_outside_provider_when_the_policy_allows_it(tmp_path: Path):
    page = client(build(tmp_path, where=Destination(True, "gemini")), user=True).get("/ask/?lang=en")

    assert "may go to an outside provider (gemini)" in page.text
    assert "looks for personal data" in page.text


def test_a_user_asks_and_reads_the_engine_and_why_in_simple_words(tmp_path: Path):
    web = client(build(tmp_path), user=True)

    sent = web.post("/ask/ask", data={"question": SECRET_QUESTION})
    page = web.get("/ask/?lang=en").text

    assert sent.status_code == 303 and sent.headers["location"] == "/ask/"
    assert "Regarde dans la corbeille." in page
    assert "Olala" in page and "stays on your machines" in page
    assert "It stayed on the machines of the house." in page


def test_the_question_is_in_the_journal_by_engine_and_reason_never_by_its_words(tmp_path: Path):
    web = client(build(tmp_path), user=True)

    web.post("/ask/ask", data={"question": SECRET_QUESTION})

    (call,) = call_journal.read(tmp_path / "ai-calls")
    assert call.caller == PORTAL_CHAT and call.kind == "question"
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert SECRET_QUESTION.encode() not in path.read_bytes(), path


def test_an_empty_question_and_a_too_long_one_are_refused_with_a_word(tmp_path: Path):
    web = client(build(tmp_path))

    assert web.post("/ask/ask", data={"question": "   "}).headers["location"] == "/ask/?notice=empty"
    assert web.post("/ask/ask", data={"question": "x" * 2001}).headers["location"] == "/ask/?notice=too_long"
    assert "Write your question first." in web.get("/ask/?notice=empty&lang=en").text


def test_when_no_allowed_engine_answers_the_page_says_so_plainly(tmp_path: Path):
    web = client(build(tmp_path, ask=silent))

    web.post("/ask/ask", data={"question": SECRET_QUESTION})
    page = web.get("/ask/?lang=en").text

    assert "No allowed engine could answer just now." in page
    assert "Olala: not reachable" in page


def test_an_engine_fault_ends_the_wait_instead_of_hanging_the_page(tmp_path: Path):
    def broken(question, operation, language, personal=()):
        raise RuntimeError("boom")

    web = client(build(tmp_path, ask=broken))

    web.post("/ask/ask", data={"question": SECRET_QUESTION})

    assert "could not be handled" in web.get("/ask/?lang=en").text


def test_each_person_sees_only_their_own_exchange_and_can_clear_it(tmp_path: Path):
    app = build(tmp_path)
    one = client(app, user=True)
    other = signed_in(TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False), name="Other", groups=())

    one.post("/ask/ask", data={"question": SECRET_QUESTION})

    assert "Regarde dans la corbeille." not in other.get("/ask/?lang=en").text
    one.post("/ask/new")
    assert "Regarde dans la corbeille." not in one.get("/ask/?lang=en").text


def test_asking_requires_the_session_s_token_and_a_session(tmp_path: Path):
    app = build(tmp_path)
    web = TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False)

    assert web.post("/ask/ask", data={"question": "x"}).status_code == 303
    signed = client(app, user=True)
    assert signed.post("/ask/ask", data={"question": "x", "csrf": "forged"}).status_code == 403


def test_the_page_is_not_served_on_the_public_port(tmp_path: Path):
    web = TestClient(build(tmp_path), base_url="http://testserver:8183", follow_redirects=False)

    assert web.get("/ask/").status_code == 404


def test_one_question_at_a_time_per_person():
    now = [0.0]
    exchanges = Exchanges(clock=lambda: now[0])

    first = exchanges.start("a", "q1")
    assert first is not None and exchanges.start("a", "q2") is None
    first.failed = True
    assert exchanges.start("a", "q3") is not None


def test_an_exchange_is_forgotten_after_half_an_hour():
    now = [0.0]
    exchanges = Exchanges(clock=lambda: now[0])
    item = exchanges.start("a", "q")
    assert item is not None
    item.failed = True

    now[0] = 1801.0

    assert exchanges.of("a") is None


def test_the_decision_is_read_from_the_route_not_from_the_content():
    answer = answered(None, "ask", "fr")

    assert decision_of(answer).engine == "Olala" and decision_of(answer).why == "stays on your machines"
    assert decision_of(replace(answer, route="")).why == ""


def test_as_shipped_the_class_allows_outside_and_the_screen_decides_per_question():
    from aistack.ai_runtime.policy import EXTERNAL_ALLOWED, current_policy

    policy = current_policy()

    assert policy.class_of(PORTAL_CHAT) == EXTERNAL_ALLOWED
    assert policy.kind_of(PORTAL_CHAT, "ask") == "question"
    assert policy.preferred("question")


def test_a_question_with_personal_data_is_screened_and_the_page_says_what_kind_not_what_words(tmp_path: Path):
    seen = {}

    def spying(question, operation, language, personal=()):
        seen["personal"] = personal
        return answered(question, operation, language)

    web = client(build(tmp_path, ask=spying), user=True)

    web.post("/ask/ask", data={"question": "ecris a jean.dupont@example.org, mon fils est grand"})
    page = web.get("/ask/?lang=en").text

    assert seen["personal"] == ("email", "family")
    assert "e-mail address, family" in page and "so your question stayed on the machines" in page
    assert "jean.dupont" in page  # the person's own question is shown back to them, in memory only
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert b"jean.dupont" not in path.read_bytes(), path


def test_a_question_with_nothing_personal_is_sent_with_no_restriction(tmp_path: Path):
    seen = {}

    def spying(question, operation, language, personal=()):
        seen["personal"] = personal
        return answered(question, operation, language)

    client(build(tmp_path, ask=spying), user=True).post("/ask/ask", data={"question": "comment regler la luminosite de l'ecran"})

    assert seen["personal"] == ()
