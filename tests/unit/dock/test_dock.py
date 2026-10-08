from __future__ import annotations

import json
import urllib.request
from urllib.parse import unquote
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.unit.web_signed_in import signed_in

from aistack.dock import proposals
from aistack.dock.candidates import inspect_all
from aistack.dock.declaration import GovernedService, load_dock_declaration
from aistack.dock.registry import parse_reference, published_digest
from aistack.i18n import Language, Languages
from aistack.sandbox.run import CommandResult
from aistack.web.app import create_app
from aistack.web.exposure import Listeners

OLD = "sha256:" + "a" * 64
NEW = "sha256:" + "b" * 64
WORDPRESS = GovernedService("wordpress", "wordpress", ("wp_app", "wordpress_db"))


def _inspect(name: str, image: str, watchtower: bool = True) -> str:
    labels = {
        "com.docker.compose.project": "wordpress",
        "com.docker.compose.service": "wordpress" if name == "wp_app" else "wordpress_db",
        "com.docker.compose.project.working_dir": "/srv/wordpress",
    }
    if watchtower:
        labels["com.centurylinklabs.watchtower.enable"] = "true"
    return json.dumps({"Image": f"sha256:id-{name}", "Config": {"Image": image, "Labels": labels}})


class FakeDocker:
    def __init__(self, *, watchtower: bool = True, missing: str = "") -> None:
        self.calls: list[list[str]] = []
        self.watchtower = watchtower
        self.missing = missing

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if args[0] == "inspect":
            name = args[-1]
            if name == self.missing:
                return CommandResult(1, "", "No such object")
            image = "wordpress:latest" if name == "wp_app" else "mariadb:11"
            return CommandResult(0, _inspect(name, image, self.watchtower))
        if args[:2] == ["image", "inspect"]:
            repository = "wordpress" if args[-1].endswith("wp_app") else "mariadb"
            return CommandResult(0, json.dumps([f"{repository}@{OLD}", f"other/{repository}@{NEW}"]))
        raise AssertionError(f"the dock asked Docker to {args}")


def publisher(image: str) -> str:
    return NEW if image.startswith("wordpress") else OLD


# -- references and the registry -------------------------------------------

@pytest.mark.parametrize(("image", "registry", "repository", "tag", "short"), [
    ("wordpress:latest", "registry-1.docker.io", "library/wordpress", "latest", "wordpress"),
    ("mariadb", "registry-1.docker.io", "library/mariadb", "latest", "mariadb"),
    ("valkey/valkey:9", "registry-1.docker.io", "valkey/valkey", "9", "valkey/valkey"),
    ("ghcr.io/immich-app/immich-server:v2.7.5", "ghcr.io", "immich-app/immich-server", "v2.7.5",
     "ghcr.io/immich-app/immich-server"),
    ("localhost:5000/team/app:1", "localhost:5000", "team/app", "1", "localhost:5000/team/app"),
])
def test_image_references_are_read_as_docker_reads_them(image, registry, repository, tag, short):
    reference = parse_reference(image)
    assert (reference.registry, reference.repository, reference.tag, reference.short_repository) == (
        registry, repository, tag, short,
    )


def test_the_published_digest_is_asked_with_an_anonymous_token():
    seen: list[urllib.request.Request] = []

    def opener(request: urllib.request.Request, timeout: float):
        seen.append(request)
        if request.full_url.startswith("https://auth.docker.io/token"):
            return 200, {}, b'{"token": "anonymous"}'
        if request.get_header("Authorization") != "Bearer anonymous":
            return 401, {"www-authenticate": 'Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'}, b""
        return 200, {"docker-content-digest": NEW}, b""

    assert published_digest("wordpress:latest", opener=opener) == NEW
    assert seen[0].get_method() == "HEAD"
    assert "scope=repository%3Alibrary%2Fwordpress%3Apull" in seen[1].full_url
    assert seen[0].full_url == "https://registry-1.docker.io/v2/library/wordpress/manifests/latest"


def test_a_registry_that_gives_no_digest_says_why():
    with pytest.raises(LookupError, match="HTTP 404"):
        published_digest("wordpress:nope", opener=lambda request, timeout: (404, {}, b""))


# -- candidates ---------------------------------------------------------------

def test_an_update_is_available_when_the_tag_now_points_elsewhere():
    found = inspect_all([WORDPRESS], FakeDocker(), publisher)

    app, db = found
    assert app.update_available and app.running_digest == OLD and app.published_digest == NEW
    assert not db.update_available
    assert app.watchtower and app.compose_dir == "/srv/wordpress" and app.compose_service == "wordpress"


def test_reading_candidates_never_pulls_or_changes_anything():
    docker = FakeDocker()
    inspect_all([WORDPRESS], docker, publisher)

    assert {call[0] for call in docker.calls} <= {"inspect", "image"}
    assert all(call[:2] != ["image", "pull"] for call in docker.calls)


def test_a_missing_container_and_an_unreachable_registry_are_said():
    def broken(image: str) -> str:
        raise OSError("timed out")

    app, db = inspect_all([WORDPRESS], FakeDocker(missing="wordpress_db"), broken)

    assert app.problem.startswith("registry not reachable") and not app.update_available
    assert db.problem == "no such container on this host"


def test_the_shipped_declaration_governs_wordpress():
    (service,) = load_dock_declaration()
    assert service.recipe == "wordpress" and service.containers == ("wp_app", "wordpress_db")


# -- proposals ------------------------------------------------------------------

CHANGE = proposals.ImageChange("wp_app", "wordpress:latest", OLD, NEW)


def test_a_change_needs_its_why(tmp_path: Path):
    with pytest.raises(proposals.ProposalRefused) as refused:
        proposals.propose(tmp_path, "wordpress", [CHANGE], "  short ", "alice")
    assert refused.value.key == "dock.refused.why"


def test_one_open_proposal_per_service(tmp_path: Path):
    proposals.propose(tmp_path, "wordpress", [CHANGE], "security release of WordPress", "alice",
                      now=datetime(2026, 10, 9, 8, tzinfo=timezone.utc))
    with pytest.raises(proposals.ProposalRefused) as refused:
        proposals.propose(tmp_path, "wordpress", [CHANGE], "another reason, same service", "bob")
    assert refused.value.key == "dock.refused.open"


def test_in_production_the_author_does_not_validate_alone(tmp_path: Path):
    proposal = proposals.propose(tmp_path, "wordpress", [CHANGE], "security release of WordPress", "alice")

    with pytest.raises(proposals.ProposalRefused) as refused:
        proposals.validate(tmp_path, proposal.id, "alice", development=False)
    assert refused.value.key == "dock.refused.same_person"

    validated = proposals.validate(tmp_path, proposal.id, "bob", development=False)
    assert validated.status == proposals.VALIDATED and validated.decided_by == "bob"
    assert [entry["event"] for entry in proposals.load(tmp_path, proposal.id).history] == ["proposed", "validated"]


def test_in_development_one_administrator_may_do_both(tmp_path: Path):
    proposal = proposals.propose(tmp_path, "wordpress", [CHANGE], "security release of WordPress", "alice")
    assert proposals.validate(tmp_path, proposal.id, "alice", development=True).status == proposals.VALIDATED


def test_a_rejected_proposal_is_closed(tmp_path: Path):
    proposal = proposals.propose(tmp_path, "wordpress", [CHANGE], "security release of WordPress", "alice")
    proposals.reject(tmp_path, proposal.id, "bob", "wait for 6.8.1")

    with pytest.raises(proposals.ProposalRefused):
        proposals.validate(tmp_path, proposal.id, "bob", development=True)
    assert proposals.load(tmp_path, proposal.id).history[-1]["detail"] == "wait for 6.8.1"


def test_a_proposal_id_cannot_reach_outside_its_folder(tmp_path: Path):
    with pytest.raises(proposals.ProposalRefused):
        proposals.load(tmp_path, "../../etc/passwd")


# -- the screen -------------------------------------------------------------------

LISTENERS = Listeners(public_port=8183, lan_port=8186)
LANGUAGES = Languages(reference="fr", available=(Language("fr", "Français"), Language("en", "English")))


def _client(tmp_path: Path, *, port: int = 8186, phase: str = "development", name: str = "Tester") -> TestClient:
    app = create_app(tmp_path, LISTENERS, LANGUAGES, phase=phase)
    app.state.dock_runner = FakeDocker()
    app.state.dock_publisher = publisher
    return signed_in(TestClient(app, base_url=f"http://testserver:{port}", follow_redirects=False), name=name)


def test_the_page_shows_the_update_and_watchtower(tmp_path: Path):
    reply = _client(tmp_path).get("/dock/?lang=en")

    assert reply.status_code == 200
    assert "update available" in reply.text
    assert "wp_app still carries Watchtower" in reply.text
    assert 'action="/dock/propose"' in reply.text


def test_nothing_answers_on_the_public_port(tmp_path: Path):
    assert _client(tmp_path, port=8183).get("/dock/").status_code == 404


def test_propose_then_validate_from_the_page(tmp_path: Path):
    client = _client(tmp_path)

    reply = client.post("/dock/propose?lang=en", data={"service": "wordpress", "why": "WordPress 6.8 security release"})
    assert reply.status_code == 303 and "status=" in reply.headers["location"]
    (proposal,) = proposals.all_proposals(tmp_path)
    assert [change.container for change in proposal.changes] == ["wp_app"]
    assert proposal.changes[0].compose_dir == "/srv/wordpress"

    client.post("/dock/validate", data={"proposal": proposal.id})
    assert proposals.load(tmp_path, proposal.id).status == proposals.VALIDATED
    assert "validée" in client.get("/dock/").text


def test_a_refusal_is_said_in_the_reader_s_language(tmp_path: Path):
    reply = _client(tmp_path).post("/dock/propose", data={"service": "wordpress", "why": "x"})

    location = unquote(reply.headers["location"])
    assert "error=" in location and "pourquoi" in location
