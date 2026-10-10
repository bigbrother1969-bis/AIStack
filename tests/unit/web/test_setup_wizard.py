"""The installation assistant's pages (ADR-0023 § 5): the token, steps 1 and 2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from aistack.authentication.definition import load_authentication_yaml
from aistack.cli import setup_token
from aistack.config import PACKAGE_ROOT
from aistack.i18n.catalog import load_catalogs, load_languages_yaml
from aistack.instance import setup_wizard as wizard
from aistack.instance.first_start import remember_copies
from aistack.instance.yaml.store import load_instance_config_yaml
from aistack.web import setup_wizard as screen
from tests.unit.web.test_rights import LAN_PORT, PUBLIC_PORT, build

SHIPPED = {
    "instance_config.yml": PACKAGE_ROOT / "instance" / "definitions" / "instance_config.yml",
    "authentication.yml": PACKAGE_ROOT / "authentication" / "definitions" / "authentication.yml",
}


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A new installation's configuration directory, as config_init fills it."""

    directory = tmp_path / "config"
    directory.mkdir()
    for name, shipped in SHIPPED.items():
        (directory / name).write_bytes(shipped.read_bytes())
    remember_copies(directory, list(SHIPPED))
    monkeypatch.setenv("AISTACK_CONFIG_DIR", str(directory))
    monkeypatch.setenv("AISTACK_CONFIG_HOST_DIR", "./config")
    return directory


def app_and_client(tmp_path: Path, port: int = LAN_PORT):
    generated = tmp_path / "generated"
    generated.mkdir(exist_ok=True)
    app = build(generated)
    asked: list[str] = []

    def fake_probe(url: str) -> wizard.Probe:
        asked.append(url)
        if url.endswith("/console.html"):
            return wizard.Probe(200, "<html>AIStack</html>")
        return wizard.Probe(200, json.dumps({"issuer": "https://id.sarfatti.fr"}))

    app.state.setup_probe = fake_probe
    app.state.asked = asked
    scheme = "https" if port == PUBLIC_PORT else "http"
    return app, generated, TestClient(app, base_url=f"{scheme}://testserver:{port}", follow_redirects=False)


def opened(tmp_path: Path, answers: str = ""):
    app, generated, web = app_and_client(tmp_path)
    token = wizard.new_token(generated)
    if answers:
        (generated / "setup" / "install.env").write_text(answers, encoding="utf-8")
    reply = web.get(f"/setup/open?token={token}")
    assert reply.status_code == 303
    return app, generated, web, token


ANSWERS = """HOST_NAME=ServerLinuX
HOST_ADDRESS=192.168.1.53
DOMAIN=sarfatti.fr
ID_NAME=id.sarfatti.fr
POCKET_ID=yes
GOTIFY=yes
SYNCTHING=yes
OLLAMA=yes
SECRET=never-read
"""


# --------------------------------------------------------------------
# The token
# --------------------------------------------------------------------


def test_without_a_token_nothing_opens(tmp_path: Path, config: Path):
    _app, _generated, web = app_and_client(tmp_path)

    for path in ("/setup/open?token=x", "/setup/step", "/setup/step/1"):
        reply = web.get(path)
        assert reply.status_code == 403, path
        assert "aistack.cli.setup_token" in reply.text
    assert web.post("/setup/step/1", data={"lan_hostname": "x"}).status_code == 403
    assert not (config / ".instance_config.yml.tmp").exists()


def test_a_wrong_token_opens_nothing(tmp_path: Path, config: Path):
    _app, generated, web = app_and_client(tmp_path)
    wizard.new_token(generated)

    assert web.get("/setup/open?token=wrong").status_code == 403
    web.cookies.set("aistack_setup", "wrong")
    assert web.get("/setup/step/1").status_code == 403


def test_the_right_token_opens_the_first_step_and_is_kept_in_a_strict_cookie(tmp_path: Path, config: Path):
    _app, generated, web = app_and_client(tmp_path)
    token = wizard.new_token(generated)

    reply = web.get(f"/setup/open?token={token}")

    assert reply.headers["location"] == "/setup/step/1"
    cookie = reply.headers["set-cookie"]
    assert "aistack_setup=" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Path=/setup" in cookie
    assert web.get("/setup/step/1?lang=fr").status_code == 200


def test_the_pages_never_answer_on_the_public_address(tmp_path: Path, config: Path):
    _app, generated, web = app_and_client(tmp_path, PUBLIC_PORT)
    token = wizard.new_token(generated)

    assert web.get(f"/setup/open?token={token}").status_code == 404


def test_the_token_file_is_private_and_finishing_closes_the_assistant(tmp_path: Path):
    from datetime import datetime

    token = wizard.new_token(tmp_path)
    assert (tmp_path / "setup" / "token").stat().st_mode & 0o777 == 0o600
    assert wizard.token_matches(tmp_path, token)

    wizard.finish(tmp_path, datetime(2026, 10, 10).astimezone())

    assert not wizard.token_matches(tmp_path, token)
    with pytest.raises(ValueError):
        wizard.new_token(tmp_path)
    assert wizard.token_matches(tmp_path, wizard.new_token(tmp_path, reopen=True))


def test_a_form_from_elsewhere_is_refused(tmp_path: Path, config: Path):
    _app, _generated, web, _token = opened(tmp_path)

    reply = web.post(
        "/setup/step/1",
        data={"form_token": "forged", "lan_hostname": "evil", "console_port": "8183", "web_lan_port": "8186", "phase": "production"},
    )

    assert reply.status_code == 403
    assert "lan_hostname: GIGABYTE" in (config / "instance_config.yml").read_text(encoding="utf-8")


# --------------------------------------------------------------------
# Step 1 — the host
# --------------------------------------------------------------------


def test_step_one_starts_from_install_sh_s_answers_never_from_the_reference_host(tmp_path: Path, config: Path):
    _app, _generated, web, token = opened(tmp_path, ANSWERS)

    page = web.get("/setup/step/1?lang=fr").text

    assert 'value="ServerLinuX"' in page
    assert "192.168.1.53" in page
    assert "GIGABYTE" not in page
    assert f'value="{wizard.form_token(token)}"' in page
    assert token not in page
    assert "./config/instance_config.yml" in page


def test_step_one_writes_the_host_and_goes_on(tmp_path: Path, config: Path):
    _app, generated, web, token = opened(tmp_path, ANSWERS)

    reply = web.post(
        "/setup/step/1",
        data={
            "form_token": wizard.form_token(token),
            "lan_hostname": "192.168.1.53",
            "console_port": "8183",
            "web_lan_port": "8186",
            "phase": "development",
        },
    )

    assert reply.status_code == 303 and reply.headers["location"] == "/setup/step/2"
    written = config / "instance_config.yml"
    loaded = load_instance_config_yaml(written)
    assert loaded.lan_hostname == "192.168.1.53"
    assert loaded.service_ports == {"console": 8183, "web_lan": 8186}
    assert loaded.phase == "development"
    assert written.read_text(encoding="utf-8").startswith("# AIStack — instance_config.yml, written by the installation assistant")
    assert 1 in wizard.progress(generated)
    # Saved, the page shows what was written, no longer install.sh's answers.
    assert 'value="192.168.1.53"' in web.get("/setup/step/1").text


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"lan_hostname": "bad name"}, "Le nom du serveur"),
        ({"console_port": "80"}, "entre 1024 et 65535"),
        ({"web_lan_port": "8183"}, "doivent être différents"),
        ({"phase": "staging"}, "Choisis une phase"),
    ],
)
def test_step_one_says_what_is_wrong_and_writes_nothing(tmp_path: Path, config: Path, data: dict, error: str):
    _app, _generated, web, token = opened(tmp_path, ANSWERS)
    before = (config / "instance_config.yml").read_bytes()
    form = {"form_token": wizard.form_token(token), "lan_hostname": "ServerLinuX", "console_port": "8183", "web_lan_port": "8186", "phase": "development"}

    reply = web.post("/setup/step/1?lang=fr", data=form | data)

    assert reply.status_code == 400
    assert error in reply.text
    assert (config / "instance_config.yml").read_bytes() == before


# --------------------------------------------------------------------
# Step 2 — the public address
# --------------------------------------------------------------------


def save_public(web: TestClient, token: str, **values: str):
    form = {"form_token": wizard.form_token(token), "domain": "sarfatti.fr", "proxy": "npm", "aistack_name": "", "id_name": ""}
    return web.post("/setup/step/2", data=form | values)


def test_step_two_derives_both_names_from_the_domain(tmp_path: Path, config: Path):
    _app, generated, web, token = opened(tmp_path, ANSWERS)

    reply = save_public(web, token, domain="https://Sarfatti.fr/")

    assert reply.status_code == 303 and reply.headers["location"] == "/setup/step/2#proxy-hosts"
    definition = load_authentication_yaml(config / "authentication.yml")
    assert definition.issuer == "https://id.sarfatti.fr"
    assert definition.public_base_url == "https://aistack.sarfatti.fr"
    # Everything else as it was.
    assert definition.admin_group == "aistack_admins"
    assert definition.client_id_env == "AISTACK_OIDC_CLIENT_ID"
    assert wizard.choices(generated) == {"domain": "sarfatti.fr", "proxy": "npm"}


def test_step_two_then_shows_the_proxy_hosts_to_create(tmp_path: Path, config: Path):
    _app, _generated, web, token = opened(tmp_path, ANSWERS)
    save_public(web, token)

    page = web.get("/setup/step/2?lang=fr").text

    assert "aistack.sarfatti.fr" in page and "id.sarfatti.fr" in page
    assert "<code>192.168.1.53</code>" in page
    assert "<code>8183</code>" in page and "<code>1411</code>" in page
    assert "Add Proxy Host" in page and "Websockets Support" in page
    # install.sh installed Pocket ID under this very name: nothing to change.
    assert "APP_URL=" not in page


def test_another_name_for_pocket_id_says_how_to_change_its_app_url(tmp_path: Path, config: Path):
    _app, _generated, web, token = opened(tmp_path, ANSWERS)
    save_public(web, token, id_name="login.sarfatti.fr")

    page = web.get("/setup/step/2").text

    assert "APP_URL=https://login.sarfatti.fr" in page
    assert "/srv/pocket-id/.env" in page


def test_another_proxy_gets_the_generic_words(tmp_path: Path, config: Path):
    _app, _generated, web, token = opened(tmp_path, ANSWERS)
    save_public(web, token, proxy="other")

    page = web.get("/setup/step/2?lang=en").text

    assert "one HTTPS virtual host per line" in page
    assert "Add Proxy Host" not in page


def test_the_check_asks_both_public_addresses(tmp_path: Path, config: Path):
    app, _generated, web, token = opened(tmp_path, ANSWERS)
    save_public(web, token)

    page = web.get("/setup/step/2?check=1&lang=en").text

    assert app.state.asked == [
        "https://aistack.sarfatti.fr/console.html",
        "https://id.sarfatti.fr/.well-known/openid-configuration",
    ]
    assert page.count("✓") >= 2 and "answers." in page


def test_a_failed_check_says_why_and_the_nat_loopback_hint(tmp_path: Path, config: Path):
    app, _generated, web, token = opened(tmp_path, ANSWERS)
    save_public(web, token)
    app.state.setup_probe = lambda url: wizard.Probe(None, "", "Name or service not known")

    page = web.get("/setup/step/2?check=1&lang=en").text

    assert "Name or service not known" in page
    assert "NAT loopback" in page


def test_pocket_id_under_another_issuer_fails_the_check():
    answer, errors = wizard.parse_public("sarfatti.fr", "npm", "", "")
    assert answer is not None and not errors

    found = wizard.check_pocket_id(answer, lambda url: wizard.Probe(200, json.dumps({"issuer": "https://other"})))

    assert not found.ok and "https://other" in found.detail


@pytest.mark.parametrize(
    ("values", "error"),
    [
        ({"domain": "localhost"}, "domain"),
        ({"aistack_name": "id.sarfatti.fr"}, "names_same"),
        ({"proxy": "apache"}, "proxy"),
        ({"id_name": "bad name"}, "id_name"),
    ],
)
def test_step_two_refuses_what_cannot_be_an_address(values: dict, error: str):
    entered = {"domain": "sarfatti.fr", "proxy": "npm", "aistack_name": "", "id_name": ""} | values

    answer, errors = wizard.parse_public(**entered)

    assert answer is None and error in errors


# --------------------------------------------------------------------
# Around the steps
# --------------------------------------------------------------------


def test_the_first_start_list_points_to_the_assistant_on_the_lan_only(tmp_path: Path, config: Path):
    _app, generated, web = app_and_client(tmp_path)
    wizard.new_token(generated)

    page = web.get("/setup?lang=fr").text
    assert "/setup/open?token=" in page and "aistack.cli.setup_token" in page

    _app, generated, public = app_and_client(tmp_path, PUBLIC_PORT)
    assert "setup_token" not in public.get("/setup?lang=fr").text


def test_once_opened_the_list_leads_back_into_the_assistant(tmp_path: Path, config: Path):
    _app, _generated, web, _token = opened(tmp_path)

    page = web.get("/setup?lang=fr").text

    assert 'href="/setup/step"' in page
    assert web.get("/setup/step").headers["location"] == "/setup/step/1"


def test_install_sh_s_answers_are_read_by_name_never_anything_else(tmp_path: Path):
    (tmp_path / "setup").mkdir()
    (tmp_path / "setup" / "install.env").write_text(ANSWERS, encoding="utf-8")

    answers = wizard.install_answers(tmp_path)

    assert answers["DOMAIN"] == "sarfatti.fr"
    assert "SECRET" not in answers


def test_the_command_shows_the_address_again(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    (tmp_path / "setup").mkdir()
    (tmp_path / "setup" / "install.env").write_text(ANSWERS, encoding="utf-8")

    assert setup_token.main(["--generated-dir", str(tmp_path)]) == 0
    first = capsys.readouterr().out.strip()
    assert first.startswith("http://192.168.1.53:8186/setup/open?token=")

    assert setup_token.main(["--generated-dir", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == first

    assert setup_token.main(["--generated-dir", str(tmp_path), "--new"]) == 0
    assert capsys.readouterr().out.strip() != first


def test_every_step_title_and_error_has_its_message():
    languages = load_languages_yaml()
    catalogs = load_catalogs(languages)
    for code in languages.codes():
        for key in list(screen.STEP_TITLES.values()) + list(screen.ERRORS.values()):
            assert key in catalogs[code], (code, key)


def test_the_written_declarations_keep_the_shipped_keys():
    shipped = yaml.safe_load(SHIPPED["instance_config.yml"].read_text(encoding="utf-8"))
    answer, _ = wizard.parse_host("ServerLinuX", "8183", "8186", "production")
    assert answer is not None

    assert set(wizard.host_declaration(shipped, answer)) == set(shipped)


# --------------------------------------------------------------------
# Step 3 — signing in
# --------------------------------------------------------------------

SECRET = "pocket-id-client-secret-0123456789abcd"
PASSWORD = "a long fallback password"


@pytest.fixture
def no_sign_in_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AISTACK_OIDC_CLIENT_ID", "AISTACK_OIDC_CLIENT_SECRET", "AISTACK_WEB_ADMIN_SCRYPT"):
        monkeypatch.delenv(name, raising=False)


def through_step_two(tmp_path: Path):
    app, generated, web, token = opened(tmp_path, ANSWERS)
    web.post(
        "/setup/step/1",
        data={"form_token": wizard.form_token(token), "lan_hostname": "192.168.1.53", "console_port": "8183", "web_lan_port": "8186", "phase": "development"},
    )
    save_public(web, token)
    return app, generated, web, token


def save_sign_in(web: TestClient, token: str, **values: str):
    form = {"form_token": wizard.form_token(token), "mode": "pocket_id", "client_id": "", "client_secret": "", "password": "", "again": ""}
    return web.post("/setup/step/3?lang=fr", data=form | values)


def test_step_three_gives_the_pocket_id_procedure_with_the_four_addresses(tmp_path: Path, config: Path, no_sign_in_environment: None):
    _app, _generated, web, _token = through_step_two(tmp_path)

    page = web.get("/setup/step/3?lang=fr").text

    assert "https://id.sarfatti.fr/setup" in page
    assert "aistack_admins" in page
    for url in (
        "https://aistack.sarfatti.fr/auth/callback",
        "http://192.168.1.53:8186/auth/callback",
        "https://aistack.sarfatti.fr/console.html",
        "http://192.168.1.53:8186/console.html",
    ):
        assert f"<code>{url}</code>" in page, url
    assert "PKCE" in page


def test_step_three_keeps_the_secrets_apart_and_never_shows_them_again(tmp_path: Path, config: Path, no_sign_in_environment: None):
    _app, generated, web, token = through_step_two(tmp_path)

    reply = save_sign_in(web, token, client_id="aistack-client", client_secret=SECRET, password=PASSWORD, again=PASSWORD)

    assert reply.status_code == 303
    store = generated / "secrets" / "sign_in.json"
    assert store.stat().st_mode & 0o777 == 0o600
    kept = json.loads(store.read_text(encoding="utf-8"))
    assert kept["AISTACK_OIDC_CLIENT_ID"] == "aistack-client"
    assert kept["AISTACK_OIDC_CLIENT_SECRET"] == SECRET
    assert kept["AISTACK_WEB_ADMIN_SCRYPT"].startswith("scrypt$")
    assert PASSWORD not in store.read_text(encoding="utf-8")
    # Not an API key: Settings never lists them.
    assert not (generated / "secrets" / "api_keys.json").exists()

    page = web.get("/setup/step/3?lang=fr").text
    assert SECRET not in page and PASSWORD not in page
    assert "…abcd" in page
    assert 'value="aistack-client"' in page
    assert 3 in wizard.progress(generated)


def test_step_three_saved_again_with_empty_fields_keeps_what_it_had(tmp_path: Path, config: Path, no_sign_in_environment: None):
    _app, generated, web, token = through_step_two(tmp_path)
    save_sign_in(web, token, client_id="aistack-client", client_secret=SECRET, password=PASSWORD, again=PASSWORD)
    before = wizard.sign_in_values(generated)

    assert save_sign_in(web, token, client_id="aistack-client").status_code == 303

    assert wizard.sign_in_values(generated) == before


@pytest.mark.parametrize(
    ("values", "error"),
    [
        ({"client_id": "", "client_secret": SECRET}, "L'identifiant du client"),
        ({"client_id": "x", "client_secret": ""}, "Le secret du client"),
        ({"client_id": "x", "client_secret": SECRET, "password": "short", "again": "short"}, "au moins 12 caractères"),
        ({"client_id": "x", "client_secret": SECRET, "password": PASSWORD, "again": PASSWORD + "!"}, "diffèrent"),
        ({"mode": "local_only"}, "Sans Pocket ID"),
    ],
)
def test_step_three_refuses_and_sends_no_secret_back(tmp_path: Path, config: Path, no_sign_in_environment: None, values: dict, error: str):
    _app, generated, web, token = through_step_two(tmp_path)

    reply = save_sign_in(web, token, **values)

    assert reply.status_code == 400
    assert error in reply.text.replace("&#39;", "'")
    assert SECRET not in reply.text and PASSWORD not in reply.text
    assert wizard.sign_in_values(generated) == {}


def test_the_fallback_administrator_alone_forgets_the_client(tmp_path: Path, config: Path, no_sign_in_environment: None):
    _app, generated, web, token = through_step_two(tmp_path)
    save_sign_in(web, token, client_id="aistack-client", client_secret=SECRET)

    assert save_sign_in(web, token, mode="local_only", password=PASSWORD, again=PASSWORD).status_code == 303

    kept = wizard.sign_in_values(generated)
    assert set(kept) == {"AISTACK_WEB_ADMIN_SCRYPT"}
    assert wizard.choices(generated)["sign_in"] == "local_only"


def test_step_three_s_check_asks_pocket_id_only(tmp_path: Path, config: Path, no_sign_in_environment: None):
    app, _generated, web, token = through_step_two(tmp_path)
    save_sign_in(web, token, client_id="aistack-client", client_secret=SECRET)
    app.state.asked.clear()

    web.get("/setup/step/3?check=1")

    assert app.state.asked == ["https://id.sarfatti.fr/.well-known/openid-configuration"]


def test_the_kept_secrets_reach_the_sign_in_when_aistack_starts(tmp_path: Path):
    wizard.keep_sign_in(tmp_path, "AISTACK_OIDC_CLIENT_ID", "aistack-client")
    environ = {"AISTACK_OIDC_CLIENT_ID": "from-env-web", "OTHER": "x"}

    wizard.apply_sign_in(tmp_path, environ)

    assert environ == {"AISTACK_OIDC_CLIENT_ID": "aistack-client", "OTHER": "x"}


def test_the_step_after_the_last_saved_one_is_offered(tmp_path: Path, config: Path, no_sign_in_environment: None):
    _app, _generated, web, _token = through_step_two(tmp_path)

    page = web.get("/setup/step/2?lang=fr").text

    assert 'href="/setup/step/3"' in page and "Étape suivante" in page


# --------------------------------------------------------------------
# Step 4 — storage
# --------------------------------------------------------------------

HOST_MOUNTS = """/dev/sda2 / ext4 rw,relatime 0 0
proc /proc proc rw 0 0
/dev/sda1 /boot/efi vfat rw 0 0
/dev/sdb1 /mnt/backup ext4 rw,relatime 0 0
/dev/sdc1 /media/david/USB ext4 rw 0 0
//nas/music /mnt/nas\\040music cifs rw 0 0
/dev/sda2 /var/lib/docker/overlay2/x overlay rw 0 0
"""


def at_step_four(tmp_path: Path):
    app, generated, web, token = opened(tmp_path, ANSWERS + "INSTALL_DIR=/srv/aistack\n")
    (generated / "setup" / "host-mounts").write_text(HOST_MOUNTS, encoding="utf-8")
    return app, generated, web, token


def test_step_four_offers_the_host_s_own_disks_never_the_system_s(tmp_path: Path, config: Path):
    _app, _generated, web, _token = at_step_four(tmp_path)

    page = web.get("/setup/step/4?lang=fr").text

    assert 'value="/mnt/backup"' in page
    assert 'value="/mnt/nas music"' in page
    # Under /media: read already. The system's and Docker's: never.
    for point in ("/media/david/USB", 'value="/"', "/boot/efi", "/var/lib/docker"):
        assert point not in page, point
    assert "<code>/media</code>" in page and "<code>/srv</code>" in page


def test_step_four_writes_the_folders_for_every_service_read_only(tmp_path: Path, config: Path):
    _app, generated, web, token = at_step_four(tmp_path)

    reply = web.post(
        "/setup/step/4",
        data={"form_token": wizard.form_token(token), "folder": ["/mnt/backup"], "typed": "/home/david/Musique/\n/media/already\n/mnt/backup\n"},
    )

    assert reply.status_code == 303
    written = yaml.safe_load((config / "volumes.yml").read_text(encoding="utf-8"))
    assert set(written["services"]) == set(wizard.SERVICES)
    assert written["services"]["vigil"]["volumes"] == [
        "/mnt/backup:/mnt/backup:ro,rslave",
        "/home/david/Musique:/home/david/Musique:ro,rslave",
    ]
    page = web.get("/setup/step/4?lang=fr").text
    assert 'value="/mnt/backup" checked' in page
    assert "/home/david/Musique" in page
    assert "COMPOSE_FILE=docker-compose.yml:config/volumes.yml" in page
    assert "cd /srv/aistack" in page
    assert 4 in wizard.progress(generated)


@pytest.mark.parametrize(
    ("typed", "error"),
    [("relative/path", "chemin absolu"), ("/etc", "du système"), ("/mnt/a:/b", "chemin absolu"), ("/", "du système")],
)
def test_step_four_refuses_what_it_must_not_read(tmp_path: Path, config: Path, typed: str, error: str):
    _app, _generated, web, token = at_step_four(tmp_path)

    reply = web.post("/setup/step/4?lang=fr", data={"form_token": wizard.form_token(token), "typed": typed})

    assert reply.status_code == 400
    assert error in reply.text
    assert not (config / "volumes.yml").exists()


def test_no_folder_gives_an_empty_override_compose_accepts():
    assert wizard.volumes_declaration([]) == {"services": {}}


def test_the_services_are_those_of_docker_compose_yml():
    from tests.unit.install.test_install_script import ROOT

    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    built_on_aistack = {name for name, service in compose["services"].items() if "tools" not in (service.get("profiles") or [])}

    assert built_on_aistack == set(wizard.SERVICES)


# --------------------------------------------------------------------
# Step 5 — API keys
# --------------------------------------------------------------------

GEMINI = "AIzaSyTHE-GEMINI-KEY-0123456789wxyz"


@pytest.fixture
def no_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from aistack import api_keys

    monkeypatch.setattr(api_keys, "_ORIGINAL", {})
    for key in api_keys.load_api_keys():
        monkeypatch.setenv(key.name, "")
        monkeypatch.delenv(key.name)


def at_step_five(tmp_path: Path, answers: str = ANSWERS):
    app, generated, web, token = opened(tmp_path, answers)
    app.state.tested = []

    def fake_test(kind: str) -> str | None:
        app.state.tested.append(kind)
        return "" if kind == "gemini" else "401 Unauthorized"

    app.state.test_api_key = fake_test
    return app, generated, web, token


def test_step_five_lists_every_key_with_its_procedure(tmp_path: Path, config: Path, no_api_keys: None):
    from aistack.api_keys import load_api_keys

    _app, _generated, web, _token = at_step_five(tmp_path)

    page = web.get("/setup/step/5?lang=fr").text

    for key in load_api_keys():
        assert f'id="key-{key.name}"' in page, key.name
    assert "https://aistudio.google.com/apikey" in page
    # {host} is the server's address, from install.sh.
    assert "http://192.168.1.53:8070" in page and "http://192.168.1.53:8384" in page
    # A setting gets a value to start from; a secret never does.
    assert 'value="http://192.168.1.53:8070"' in page


def test_step_five_keeps_a_key_like_settings_and_never_shows_it(tmp_path: Path, config: Path, no_api_keys: None):
    import os

    app, generated, web, token = at_step_five(tmp_path)

    reply = web.post(
        "/setup/step/5",
        data={"form_token": wizard.form_token(token), "name": "AISTACK_GEMINI_API_KEY", "value": GEMINI, "action": "save"},
    )

    assert reply.status_code == 303
    assert reply.headers["location"].endswith("#key-AISTACK_GEMINI_API_KEY")
    kept = json.loads((generated / "secrets" / "api_keys.json").read_text(encoding="utf-8"))
    assert kept == {"AISTACK_GEMINI_API_KEY": GEMINI}
    assert os.environ["AISTACK_GEMINI_API_KEY"] == GEMINI
    page = web.get(reply.headers["location"].split("#")[0] + "&lang=fr").text
    assert GEMINI not in page and "…wxyz" in page
    assert "AISTACK_GEMINI_API_KEY enregistrée." in page


def test_step_five_tests_a_key_and_says_why_it_was_refused(tmp_path: Path, config: Path, no_api_keys: None):
    app, _generated, web, token = at_step_five(tmp_path)
    form = {"form_token": wizard.form_token(token), "action": "save"}
    web.post("/setup/step/5", data=form | {"name": "AISTACK_GOTIFY_TOKEN", "value": "AbCdEfGhIjKl"})

    reply = web.post("/setup/step/5", data=form | {"name": "AISTACK_GOTIFY_TOKEN", "action": "test"})
    page = web.get(reply.headers["location"].split("#")[0] + "&lang=fr").text

    assert app.state.tested == ["gotify"]
    assert "401 Unauthorized" in page


def test_a_prerequisite_install_sh_skipped_is_said_optional(tmp_path: Path, config: Path, no_api_keys: None):
    _app, _generated, web, _token = at_step_five(tmp_path, ANSWERS.replace("GOTIFY=yes", "GOTIFY=no"))

    page = web.get("/setup/step/5?lang=fr").text

    assert page.count("install.sh ne l&#39;a pas installé") == 2


def test_step_five_is_done_when_the_owner_says_so(tmp_path: Path, config: Path, no_api_keys: None):
    _app, generated, web, token = at_step_five(tmp_path)

    reply = web.post("/setup/step/5", data={"form_token": wizard.form_token(token), "action": "done"})

    assert reply.status_code == 303
    assert 5 in wizard.progress(generated)
    assert not (generated / "secrets" / "api_keys.json").exists()


def test_settings_shows_each_key_s_procedure_too():
    from aistack.api_keys import load_api_keys

    for key in load_api_keys():
        assert key.steps("fr") and key.steps("en"), key.name
