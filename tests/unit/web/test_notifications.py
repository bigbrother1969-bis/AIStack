"""
The notice on every page when an AI answer is ready (owner, 2026-10-09):
`aistack.web.ai_jobs`, `/notifications`, and the snippet the middleware
puts before `</body>`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aistack.web.ai_jobs import AIJobs
from tests.unit.web.test_troubleshooting_router import LAN_PORT, PUBLIC_PORT, Host, client, host  # noqa: F401

STEP_2 = "/troubleshooting/finding/newcomer/step/2"


def test_a_job_s_answers_are_ready_for_its_owner_only_until_opened():
    clock = iter(range(100))
    jobs = AIJobs(clock=lambda: next(clock))
    jobs.start("job", "alice", "newcomer", expected=2)
    jobs.answered("job", "troubleshooting.step.reason", "/a")

    running, ready = jobs.for_owner("alice")
    assert running == 1 and [item.href for _, item in ready] == ["/a"]
    assert jobs.for_owner("bob") == (0, [])

    jobs.answered("job", "troubleshooting.step.explain", "/b")
    jobs.seen("alice", "/a")
    running, ready = jobs.for_owner("alice")
    assert running == 0 and [item.href for _, item in ready] == ["/b"]


def test_each_answer_of_a_diagnosis_is_announced_with_its_step(tmp_path: Path, host: Host):  # noqa: F811
    web = client(tmp_path, host)
    web.post("/troubleshooting/finding/newcomer/start")

    reply = web.get("/notifications")

    assert reply.status_code == 200
    data = reply.json()
    assert data["running"] == 0
    assert sorted(item["href"] for item in data["ready"]) == [
        STEP_2, "/troubleshooting/finding/newcomer/step/3", "/troubleshooting/finding/newcomer/step/4",
    ]
    assert any("Raisonnement" in item["text"] and "newcomer" in item["text"] for item in data["ready"])


def test_opening_an_answer_takes_it_off_the_notices(tmp_path: Path, host: Host):  # noqa: F811
    web = client(tmp_path, host)
    web.post("/troubleshooting/finding/newcomer/start")

    web.get(STEP_2)

    hrefs = [item["href"] for item in web.get("/notifications").json()["ready"]]
    assert STEP_2 not in hrefs and len(hrefs) == 2


def test_a_diagnosis_still_running_is_counted(tmp_path: Path, host: Host):  # noqa: F811
    web = client(tmp_path, host, background=True)
    web.post("/troubleshooting/finding/newcomer/start")

    assert web.get("/notifications").json() == {"running": 1, "ready": []}


def test_every_lan_page_of_a_signed_in_person_carries_the_notice(tmp_path: Path, host: Host):  # noqa: F811
    page = client(tmp_path, host).get("/troubleshooting/")

    assert 'id="aistack-notices"' in page.text
    assert page.text.index('id="aistack-notices"') < page.text.rindex("</body>")
    assert '"Fermer cette notification"' in page.text


def test_no_notice_on_the_public_port_nor_signed_out(tmp_path: Path, host: Host):  # noqa: F811
    public = client(tmp_path, host, port=PUBLIC_PORT).get("/console.html")
    assert 'id="aistack-notices"' not in public.text

    web = client(tmp_path, host)
    anonymous = TestClient(web.app, base_url=f"http://testserver:{LAN_PORT}")
    assert 'id="aistack-notices"' not in anonymous.get("/login").text
    assert anonymous.get("/notifications").json() == {"running": 0, "ready": []}
