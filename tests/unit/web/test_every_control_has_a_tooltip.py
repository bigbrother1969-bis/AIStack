"""
Every control on every page carries a tooltip (the owner, 2026-10-03:
"prévoir aussi des info-bulles partout" — "les infos bulles
s'appliquent sur toutes les pages").

Each page is rendered as a visitor receives it — the console's
generated pages through their renderers, every screen through the web
application with its host collaborators replaced — and every link,
button, field, list and foldable summary in it must carry a `title`.
Controls a page's own script builds after loading are not in this HTML
and are held to the same rule in their templates by review. A link
inside an SVG drawing carries its tooltip the SVG way, as a `<title>`
element it contains.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack.architecture.graph import ArchitectureGraph, CategoryGraph, ServiceNode, ServiceStatus
from aistack.architecture.views import build_all_views
from aistack.console.identity import load_console_identity
from aistack.console.yaml import load_console_links_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.contracts.backup_gap import MISSING, BackupGap
from aistack.contracts.backup_reading import BackupReading
from aistack.contracts.health_score import TO_WATCH, HealthScore
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.i18n import Language, Languages
from aistack.network_discovery.definition import NetworkDiscoveryDefinition
from aistack.network_discovery.yaml import save_network_discovery_yaml
from aistack.priority.discovery import DiscoveredContainer
from aistack.renderers.architecture.html import render_html as render_architecture
from aistack.renderers.console.html import render_html as render_console
from aistack.renderers.console.pages import render_help_html, render_legal_html, render_license_html
from aistack.renderers.console.settings import render_settings_html
from aistack.renderers.health.html import render_html as render_health
from aistack.runtime.evaluate_backup import evaluate_backup
from aistack.troubleshooting.findings import CONSUMPTION_DOMAIN, qualify
from aistack.web.app import PACKAGE_ROOT, WebPaths, create_app
from aistack.web.exposure import Listeners
from tests.unit.timemachine_sample import build_sample_graph, sample_tree

CONTROLS = {"a", "button", "select", "input", "textarea", "summary"}

LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


class Untitled(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.missing: list[str] = []
        self.svg_depth = 0
        self.svg_link: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = dict(attrs)

        if tag == "svg":
            self.svg_depth += 1

        if self.svg_depth:
            if tag == "a":
                self.svg_link = self.get_starttag_text() or tag
            elif tag == "title":
                self.svg_link = None
            return

        if tag not in CONTROLS:
            return

        if tag == "input" and names.get("type") == "hidden":
            return

        if tag == "a" and "href" not in names:
            return

        if not (names.get("title") or "").strip():
            self.missing.append(self.get_starttag_text() or tag)


    def handle_endtag(self, tag: str) -> None:
        if self.svg_depth and tag == "a" and self.svg_link is not None:
            self.missing.append(self.svg_link)
            self.svg_link = None
        if tag == "svg":
            self.svg_depth -= 1


def untitled(html: str) -> list[str]:
    parser = Untitled()
    parser.feed(html)

    return parser.missing


def a_finding():
    (finding,) = evaluate_backup(
        [
            BackupGap(
                reading=BackupReading(path="/media/BACKUP/x", observed_at=datetime.now(timezone.utc)),
                max_age_hours=36.0,
                reason=MISSING,
            )
        ]
    )
    return finding


def generated_pages() -> dict[str, str]:
    links = load_console_links_yaml(
        PACKAGE_ROOT / "console" / "definitions" / "console_links.yml", lang="fr"
    )
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True),
            HealthDomain(name="Sauvegarde / PRA", instrumented=True, findings=(a_finding(),)),
            HealthDomain(name="GPU", instrumented=False, note="no GPU"),
        )
    )
    identity = load_console_identity(lang="fr")
    graph = ArchitectureGraph(
        categories=(
            CategoryGraph(
                name="Média",
                services=(
                    ServiceNode(
                        name="Jellyfin",
                        category="Média",
                        container=None,
                        status=ServiceStatus.NO_CONTAINER,
                        icon=None,
                        href="https://jellyfin.example",
                        description=None,
                    ),
                ),
            ),
        )
    )

    return {
        "console": render_console(
            links,
            cockpit,
            HealthScore(value=81, measured_domains=2, total_domains=3, bucket=TO_WATCH),
            lang="fr",
            identity=identity,
        ),
        "settings": render_settings_html("fr"),
        "help": render_help_html("fr"),
        "legal": render_legal_html(identity, "fr"),
        "license": render_license_html(identity, "fr"),
        "health": render_health(cockpit, lang="fr", troubleshooting_base_url="http://GIGABYTE:8186/troubleshooting"),
        "architecture": render_architecture(build_all_views(graph), lang="fr"),
    }


@pytest.mark.parametrize("page", sorted(generated_pages()))
def test_every_control_of_a_generated_page_has_a_tooltip(page: str):
    assert untitled(generated_pages()[page]) == []


def answer(finding, operation: str, language: str) -> AIRuntimeAnswer:
    return AIRuntimeAnswer(
        operation=operation,
        subject=finding.subject,
        model="fake",
        prompt="p",
        response="r",
        reachable=True,
        unreachable_reason="",
    )


@pytest.fixture
def web(tmp_path: Path) -> TestClient:
    priority = tmp_path / "resource_priority.yml"
    shutil.copy(PACKAGE_ROOT / "priority" / "definitions" / "resource_priority.yml", priority)
    discovery = tmp_path / "network_discovery.yml"
    save_network_discovery_yaml(
        NetworkDiscoveryDefinition(cidr="192.168.1.0/24", ssh_key_path_env="K", ssh_usernames=("pi",)),
        discovery,
    )
    library = tmp_path / "library" / "Artist" / "Album"
    library.mkdir(parents=True)
    (library / "01.mp3").write_bytes(b"x")
    (tmp_path / "phone").mkdir()
    selection = tmp_path / "music_android.yml"
    selection.write_text(
        "app_id: music_android\ntitle: Music\nview_id: media-tree\n"
        f"source_root: {tmp_path / 'library'}\ntarget_root: {tmp_path / 'phone'}\n"
        "selection_file: selections/m.yml\ncapacity_declared_bytes: 1000000\n",
        encoding="utf-8",
    )
    consumption = a_finding()

    app = create_app(
        tmp_path,
        Listeners(public_port=8183, lan_port=8186),
        LANGUAGES,
        WebPaths(
            network_discovery=discovery,
            resource_priority=priority,
            selection=selection,
            repository_root=tmp_path,
        ),
        discover=lambda: (DiscoveredContainer(name="jellyfin", image="j", running=True, status="Up"),),
        syncthing=lambda definition: None,
        collect_findings=lambda: (qualify([(CONSUMPTION_DOMAIN, consumption)]), ""),
        ask_ai=answer,
        run_in_background=lambda job: job(),
        network_tree=sample_tree,
    )
    build_sample_graph(tmp_path)
    client = TestClient(app, base_url="http://testserver:8186", follow_redirects=False)
    key = "%2Fmedia%2FBACKUP%2Fx"
    client.post(f"/troubleshooting/finding/{key}/start")
    client.post(f"/troubleshooting/finding/{key}/apply")

    return client


SCREENS = [
    "/network-discovery/?status=ok",
    "/priority/?status=ok",
    "/selection/?status=ok",
    "/troubleshooting/?status=ok",
    "/troubleshooting/aide",
    "/troubleshooting/finding/%2Fmedia%2FBACKUP%2Fx/step/1",
    "/troubleshooting/finding/%2Fmedia%2FBACKUP%2Fx/step/4",
    "/troubleshooting/finding/%2Fmedia%2FBACKUP%2Fx/applied",
    "/timemachine/",
    "/timemachine/tree",
    "/timemachine/tree?q=booklore",
    "/timemachine/ribbon",
    "/timemachine/ribbon?subject=booklore_db",
    "/timemachine/node?iri=urn%3Aaistack%3Astream%3Apriority-decision",
    "/timemachine/node?iri=urn%3Aaistack%3Aobservation%3Apriority-decision%3A2026-10-01T10-00-00Z",
    "/timemachine/reconstitute?subject=booklore_db&as_of=2026-10-02T23:00:00Z",
    "/timemachine/explication?subject=booklore_db",
]


def test_without_a_graph_the_time_machine_page_has_no_untitled_control(tmp_path: Path):
    app = create_app(
        tmp_path, Listeners(public_port=8183, lan_port=8186), LANGUAGES, network_tree=sample_tree
    )
    reply = TestClient(app, base_url="http://testserver:8186").get("/timemachine/")

    assert reply.status_code == 200
    assert untitled(reply.text) == []


@pytest.mark.parametrize("path", SCREENS)
def test_every_control_of_a_screen_has_a_tooltip(web: TestClient, path: str):
    reply = web.get(path)

    assert reply.status_code == 200
    assert untitled(reply.text) == []


def test_the_sign_in_pages_have_no_untitled_control(tmp_path: Path):
    from aistack.authentication.local_admin import hash_password
    from aistack.authentication.oidc import OidcClient
    from aistack.authentication.sessions import LOCAL, SessionStore
    from aistack.web.authentication import SESSION_COOKIE, Authentication
    from tests.unit.authentication_fake import CREDENTIALS, DEFINITION, FakeProvider

    credentials = type(CREDENTIALS)(
        client_id=CREDENTIALS.client_id,
        client_secret=CREDENTIALS.client_secret,
        local_admin_hash=hash_password("a fallback password"),
    )
    sessions = SessionStore(tmp_path / "s.sqlite3", 3600, 86400)
    auth = Authentication(DEFINITION, credentials, sessions, OidcClient(DEFINITION, credentials, FakeProvider()))
    (tmp_path / "console.html").write_text(generated_pages()["console"], encoding="utf-8")
    app = create_app(tmp_path, Listeners(public_port=8183, lan_port=8186), LANGUAGES, auth=auth)
    lan = TestClient(app, base_url="http://testserver:8186", follow_redirects=False)

    assert untitled(lan.get("/login/local").text) == []
    assert untitled(lan.get("/console.html").text) == []

    lan.cookies.set(SESSION_COOKIE, sessions.open(subject="x", name="x", method=LOCAL))
    signed_in = lan.get("/console.html").text
    assert 'action="/logout"' in signed_in
    assert untitled(signed_in) == []
