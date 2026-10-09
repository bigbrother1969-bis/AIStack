"""
*Assistant de pannes* inside AIStack's single web application
(`ADR-0012`). The host's findings and Ollama are replaced; the
resource-priority definition and the reasoning history are written
under temporary paths, for real.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.resource_reading import ContainerCpuReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.i18n import Language, Languages
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.troubleshooting.findings import CONSUMPTION_DOMAIN, qualify
from aistack.web.app import PACKAGE_ROOT, WebPaths, create_app
from aistack.web.exposure import Listeners

PUBLIC_PORT = 8183
LAN_PORT = 8186
LISTENERS = Listeners(public_port=PUBLIC_PORT, lan_port=LAN_PORT)
LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


def finding(subject: str) -> RuntimeFinding:
    return RuntimeFinding(
        subject=subject,
        signature="OPS-0001/S-003",
        interpretation="unexplained CPU consumption",
        remediation=f"declare {subject} in resource_priority.yml",
        confidence="high",
        grounding=f"OPS-0003/{subject}",
        evidence=(
            CitedReading(
                provider="aistack.provider.docker",
                reading=ContainerCpuReading(container=subject, cpu_percent=12.2),
            ),
        ),
        qualifications=("OPS-0004/sustainability-anomaly",),
    )


def answer(found: RuntimeFinding, operation: str, language: str) -> AIRuntimeAnswer:
    return AIRuntimeAnswer(
        operation=operation,
        subject=found.subject,
        model="fake",
        prompt=f"{operation} in {language}",
        response=f"{operation} answer for **{found.subject}**",
        reachable=True,
        unreachable_reason="",
    )


class Host:
    """The findings the host reports; a fix on the consumption finding clears it."""

    def __init__(self, definition: Path) -> None:
        self.definition = definition
        self.asked: list[tuple[str, str, str]] = []
        self.queued: list[object] = []
        self.contexts: list[str] = []
        # A calmer reading: the CPU finding is no longer seen.
        self.calm = False
        self.resolved = False

    def collect(self):
        background = {
            c.name for c in load_resource_priority_yaml(self.definition).background.containers
        }
        tagged = [("Tests PRA", finding("nextcloud")), ("État persistant", finding("nextcloud"))]
        if not self.resolved:
            tagged.append(("Tests PRA", finding("gigabyte")))

        if "newcomer" not in background and not self.calm:
            tagged.insert(0, (CONSUMPTION_DOMAIN, finding("newcomer")))

        return qualify(tagged), ""

    def ask(self, found: RuntimeFinding, operation: str, language: str, context: str = ""):
        self.asked.append((found.subject, operation, language))
        self.contexts.append(context)
        return answer(found, operation, language)


@pytest.fixture
def host(tmp_path: Path) -> Host:
    path = tmp_path / "resource_priority.yml"
    shutil.copy(PACKAGE_ROOT / "priority" / "definitions" / "resource_priority.yml", path)

    return Host(path)


def client(
    tmp_path: Path, host: Host, port: int = LAN_PORT, background: bool = False, destination=("ollama", "qwen2.5:3b")
) -> TestClient:
    """`background=True` keeps the diagnosis queued instead of running it at once."""

    app = create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        WebPaths(resource_priority=host.definition),
        collect_findings=host.collect,
        ask_ai=host.ask,
        destination=lambda: destination,
        run_in_background=host.queued.append if background else (lambda job: job()),
    )

    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False))


@pytest.mark.parametrize("path", ["/troubleshooting", "/troubleshooting/"])
def test_the_list_shows_every_finding_with_its_routing_key(tmp_path: Path, host: Host, path: str):
    reply = client(tmp_path, host).get(f"{path}?lang=en")

    assert reply.status_code == 200
    assert 'action="/troubleshooting/finding/newcomer/start"' in reply.text
    assert "Tests%20PRA%3A%3Anextcloud" in reply.text or "Tests PRA::nextcloud" in unquote(reply.text)
    assert 'href="/troubleshooting/aide"' in reply.text
    assert 'href="/console.html?lang=en"' in reply.text


def test_the_help_page_is_served(tmp_path: Path, host: Host):
    assert client(tmp_path, host).get("/troubleshooting/aide").status_code == 200


def test_starting_shows_aistack_s_own_facts_and_asks_no_ai(tmp_path: Path, host: Host):
    web = client(tmp_path, host)

    reply = web.post("/troubleshooting/finding/newcomer/start?lang=en")

    assert reply.status_code == 303
    assert reply.headers["location"] == "/troubleshooting/finding/newcomer/step/1"
    assert host.asked == []

    facts = web.get("/troubleshooting/finding/newcomer/step/2?lang=en").text
    assert "Container" in facts and "newcomer" in facts and "12.2" in facts
    assert "Class in resource_priority.yml" in facts and "unclassified" in facts

    todo = web.get("/troubleshooting/finding/newcomer/step/3?lang=en").text
    assert 'action="/troubleshooting/finding/newcomer/apply"' in todo
    assert "docker stats --no-stream newcomer" in todo

    opinion = web.get("/troubleshooting/finding/newcomer/step/4?lang=en").text
    assert 'action="/troubleshooting/finding/newcomer/ask"' in opinion
    assert 'http-equiv="refresh"' not in opinion
    assert host.asked == []


def test_asking_the_ai_runs_the_three_operations_once_and_records_them(tmp_path: Path, host: Host):
    web = client(tmp_path, host)
    web.post("/troubleshooting/finding/newcomer/start?lang=en")

    reply = web.post("/troubleshooting/finding/newcomer/ask?lang=en")

    assert reply.headers["location"] == "/troubleshooting/finding/newcomer/step/4"
    assert host.asked == [
        ("newcomer", "reason", "en"),
        ("newcomer", "explain", "en"),
        ("newcomer", "recommend", "en"),
    ]
    assert list((tmp_path / "ai-reasoning").glob("newcomer*"))
    # The facts of step 2 go with the question (2026-10-09).
    assert all("CPU (%): 12.2" in context for context in host.contexts)
    page = web.get("/troubleshooting/finding/newcomer/step/4").text
    assert "recommend answer for newcomer" in page and 'id="ai-reason"' in page
    assert "**" not in page
    assert 'action="/troubleshooting/finding/newcomer/ask"' not in page


def test_a_backup_gap_says_where_to_declare_its_real_copy(tmp_path: Path, host: Host):
    from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration
    from aistack.contracts.uncovered_state_gap import UncoveredStateGap
    from aistack.runtime.evaluate_uncovered_state import evaluate_uncovered_state

    (gap,) = evaluate_uncovered_state(
        [
            UncoveredStateGap(
                declaration=BackupStrategyDeclaration(
                    service="nextcloud-files",
                    host="GIGABYTE",
                    has_state=True,
                    engines=(),
                    mechanism="aucun — une seule copie",
                )
            )
        ]
    )
    app = create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        WebPaths(resource_priority=host.definition),
        collect_findings=lambda: (qualify([("État persistant", gap)]), ""),
        ask_ai=host.ask,
        run_in_background=lambda job: job(),
    )
    web = signed_in(TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False))
    web.post("/troubleshooting/finding/nextcloud-files/start")

    facts = web.get("/troubleshooting/finding/nextcloud-files/step/2?lang=fr").text
    assert "Mécanisme" not in facts or "aucun — une seule copie" in facts
    assert "aucun — une seule copie" in facts and "GIGABYTE" in facts
    todo = web.get("/troubleshooting/finding/nextcloud-files/step/3?lang=fr").text
    assert "./config/backup_strategy.yml" in todo
    assert "  - name: nextcloud-files" in todo and "host: GIGABYTE" in todo
    assert "/apply" not in todo
    assert host.asked == []


def test_an_unknown_key_goes_back_to_the_list(tmp_path: Path, host: Host):
    reply = client(tmp_path, host).post("/troubleshooting/finding/nowhere/start")

    assert reply.status_code == 303
    assert reply.headers["location"].startswith("/troubleshooting/?status=")
    assert host.asked == []


def test_a_cpu_finding_the_list_showed_starts_though_the_next_reading_is_calm(tmp_path: Path, host: Host):
    web = client(tmp_path, host)
    assert "newcomer" in web.get("/troubleshooting/").text
    host.calm = True

    reply = web.post("/troubleshooting/finding/newcomer/start")

    assert reply.headers["location"] == "/troubleshooting/finding/newcomer/step/1"
    assert "newcomer" in web.get("/troubleshooting/finding/newcomer/step/2").text


def test_a_cockpit_finding_gone_since_the_list_is_resolved(tmp_path: Path, host: Host):
    web = client(tmp_path, host)
    assert "gigabyte" in web.get("/troubleshooting/").text
    host.resolved = True

    reply = web.post("/troubleshooting/finding/gigabyte/start")

    assert reply.headers["location"].startswith("/troubleshooting/?status=")
    assert host.asked == []


def test_a_step_without_a_session_goes_back_to_the_list(tmp_path: Path, host: Host):
    reply = client(tmp_path, host).get("/troubleshooting/finding/newcomer/step/2")

    assert reply.status_code == 303
    assert reply.headers["location"].startswith("/troubleshooting/?status=")


def test_the_fix_writes_the_definition_and_checks_the_finding_is_gone(tmp_path: Path, host: Host):
    web = client(tmp_path, host)
    web.post("/troubleshooting/finding/newcomer/start")

    reply = web.post("/troubleshooting/finding/newcomer/apply")

    assert reply.status_code == 303
    assert reply.headers["location"] == "/troubleshooting/finding/newcomer/applied"
    assert "newcomer" in {
        c.name for c in load_resource_priority_yaml(host.definition).background.containers
    }
    page = web.get("/troubleshooting/finding/newcomer/applied")
    assert page.status_code == 200


def test_the_fix_is_refused_for_a_finding_of_another_domain(tmp_path: Path, host: Host):
    web = client(tmp_path, host)
    key = "Tests PRA::nextcloud"
    web.post(f"/troubleshooting/finding/{key}/start")
    before = host.definition.read_bytes()

    reply = web.post(f"/troubleshooting/finding/{key}/apply")

    assert reply.status_code == 303
    assert reply.headers["location"].startswith("/troubleshooting/?status=")
    assert host.definition.read_bytes() == before


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/troubleshooting/"),
        ("GET", "/troubleshooting/aide"),
        ("POST", "/troubleshooting/finding/newcomer/start"),
        ("POST", "/troubleshooting/finding/newcomer/apply"),
        ("POST", "/troubleshooting/finding/newcomer/ask"),
    ],
)
def test_nothing_answers_asks_or_writes_on_the_public_port(
    tmp_path: Path, host: Host, method: str, path: str
):
    before = host.definition.read_bytes()

    reply = client(tmp_path, host, PUBLIC_PORT).request(method, path)

    assert reply.status_code == 404
    assert host.asked == []
    assert host.definition.read_bytes() == before


def test_the_ai_step_waits_for_answers_still_being_computed(tmp_path: Path, host: Host):
    web = client(tmp_path, host, background=True)
    web.post("/troubleshooting/finding/newcomer/start?lang=en")

    reply = web.post("/troubleshooting/finding/newcomer/ask?lang=en")

    assert reply.headers["location"] == "/troubleshooting/finding/newcomer/step/4"
    assert len(host.queued) == 1 and host.asked == []

    facts = web.get("/troubleshooting/finding/newcomer/step/2")
    pending = web.get("/troubleshooting/finding/newcomer/step/4?lang=en")

    assert 'http-equiv="refresh"' not in facts.text
    assert 'http-equiv="refresh"' in pending.text
    assert "The AI model is working" in pending.text

    host.queued[0]()  # the background worker runs the diagnosis

    done = web.get("/troubleshooting/finding/newcomer/step/4")
    assert "reason answer for newcomer" in done.text
    assert 'http-equiv="refresh"' not in done.text
    assert list((tmp_path / "ai-reasoning").glob("newcomer*"))


def test_the_ai_is_asked_once_per_session(tmp_path: Path, host: Host):
    web = client(tmp_path, host, background=True)

    web.post("/troubleshooting/finding/newcomer/start")
    web.post("/troubleshooting/finding/newcomer/ask")
    web.post("/troubleshooting/finding/newcomer/start")
    web.post("/troubleshooting/finding/newcomer/ask")

    assert len(host.queued) == 1


def test_the_page_says_the_question_leaves_the_house_before_the_click(tmp_path: Path, host: Host):
    web = client(tmp_path, host, destination=("gemini", "gemini-x"))
    web.post("/troubleshooting/finding/newcomer/start")

    page = web.get("/troubleshooting/finding/newcomer/step/4?lang=fr").text

    assert "Envoyé à Google Gemini (gemini-x), hors de ton réseau" in page
    local = client(tmp_path, host).get("/troubleshooting/").text
    assert local


def test_asking_without_a_session_goes_back_to_the_list(tmp_path: Path, host: Host):
    reply = client(tmp_path, host).post("/troubleshooting/finding/newcomer/ask")

    assert reply.headers["location"].startswith("/troubleshooting/?status=")
    assert host.asked == []


def test_an_engine_that_gave_no_answer_is_said_in_the_reader_s_language(tmp_path: Path, host: Host):
    def silent(found: RuntimeFinding, operation: str, language: str, context: str = "") -> AIRuntimeAnswer:
        return AIRuntimeAnswer(
            operation=operation,
            subject=found.subject,
            model="deepseek-r1:1.5b",
            prompt="p",
            response="",
            reachable=False,
            unreachable_reason="Ollama at 127.0.0.1:11434 did not answer within 900.0 seconds",
        )

    app = create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        WebPaths(resource_priority=host.definition),
        collect_findings=host.collect,
        ask_ai=silent,
        run_in_background=lambda job: job(),
    )
    web = signed_in(TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False))
    web.post("/troubleshooting/finding/newcomer/start?lang=fr")
    web.post("/troubleshooting/finding/newcomer/ask?lang=fr")

    page = web.get("/troubleshooting/finding/newcomer/step/4?lang=fr").text

    assert "pas de réponse dans le délai déclaré (900 s)" in page
    assert "did not answer" not in page


def test_a_finding_is_shown_in_the_reader_s_language(tmp_path: Path, host: Host):
    from datetime import datetime, timezone

    from aistack.contracts.backup_gap import MISSING, BackupGap
    from aistack.contracts.backup_reading import BackupReading
    from aistack.runtime.evaluate_backup import evaluate_backup

    (backup,) = evaluate_backup(
        [
            BackupGap(
                reading=BackupReading(
                    path="/media/BACKUP/nextcloud", observed_at=datetime.now(timezone.utc)
                ),
                max_age_hours=36.0,
                reason=MISSING,
            )
        ]
    )
    app = create_app(
        tmp_path,
        LISTENERS,
        LANGUAGES,
        WebPaths(resource_priority=host.definition),
        collect_findings=lambda: (qualify([("Sauvegarde / PRA", backup)]), ""),
        ask_ai=host.ask,
        run_in_background=lambda job: job(),
    )
    web = signed_in(TestClient(app, base_url=f"http://testserver:{LAN_PORT}", follow_redirects=False))

    listing = web.get("/troubleshooting/?lang=fr").text
    web.post("/troubleshooting/finding/%2Fmedia%2FBACKUP%2Fnextcloud/start")
    step = web.get("/troubleshooting/finding/%2Fmedia%2FBACKUP%2Fnextcloud/step/1?lang=fr")

    assert "ne contient aucun fichier de sauvegarde" in listing
    assert "holds no backup file" not in listing
    assert step.status_code == 200
    assert "Mesuré" in step.text
    todo = web.get("/troubleshooting/finding/%2Fmedia%2FBACKUP%2Fnextcloud/step/3?lang=fr").text
    assert "Vérifier que la tâche de sauvegarde" in todo
    assert "systemctl list-timers" in todo
