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
