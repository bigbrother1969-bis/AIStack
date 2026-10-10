"""
The installation assistant's pages, their state and what they write
(`ADR-0023` § 5).

**The installation token.** `install.sh` writes a random token in the
data directory (`setup/token`, mode 0600) and shows the address that
opens the assistant with it; until then — and once the assistant is
finished — nobody can use the pages, and the read-only `/setup` list
stays what it was (`ADR-0017` § 4). The token lives until the assistant
is finished; `python -m aistack.cli.setup_token` shows it again when
the address was lost, or makes a new one.

**What install.sh answered.** `setup/install.env` — the host's name and
address, the domain and the prerequisites installed — fills the
pages' first values; never a secret.

**What the pages write.** The declarations of the configuration
directory (`instance_config.yml`, `authentication.yml`), whole, with a
header saying who wrote them; each step saved is recorded in
`setup/progress.json`. Nothing is read again before AIStack restarts,
which the last step says how to do.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

SETUP_FOLDER = "setup"
# The cookie the pages read the token from, set by `/setup/open`.
COOKIE = "aistack_setup"
TOKEN_FILE = "token"
FINISHED_FILE = "finished"
ANSWERS_FILE = "install.env"
PROGRESS_FILE = "progress.json"
CHOICES_FILE = "choices.json"

# What install.sh may write in `install.env`: nothing else is read.
ANSWER_KEYS = (
    "HOST_NAME",
    "HOST_ADDRESS",
    "DOMAIN",
    "ID_NAME",
    "POCKET_ID",
    "GOTIFY",
    "SYNCTHING",
    "OLLAMA",
)

DEVELOPMENT = "development"
PRODUCTION = "production"
PHASES = (DEVELOPMENT, PRODUCTION)

NGINX_PROXY_MANAGER = "npm"
OTHER_PROXY = "other"
PROXIES = (NGINX_PROXY_MANAGER, OTHER_PROXY)

# Pocket ID's port, as `deploy/prerequisites/pocket-id/compose.yml` publishes it.
POCKET_ID_PORT = 1411

_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_HOST_NAME = re.compile(rf"^(?=.{{1,253}}$){_LABEL}(?:\.{_LABEL})*$")


def folder(generated: Path) -> Path:
    return generated / SETUP_FOLDER


# --------------------------------------------------------------------
# The token
# --------------------------------------------------------------------


def finished(generated: Path) -> bool:
    return (folder(generated) / FINISHED_FILE).is_file()


def read_token(generated: Path) -> str | None:
    """The token that opens the pages, or None: none made, or the
    assistant finished."""

    if finished(generated):
        return None
    try:
        token = (folder(generated) / TOKEN_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def is_open(generated: Path) -> bool:
    return read_token(generated) is not None


def token_matches(generated: Path, offered: str | None) -> bool:
    token = read_token(generated)
    if not token or not offered:
        return False
    return hmac.compare_digest(token.encode(), offered.encode())


def form_token(token: str) -> str:
    """What each form carries: derived from the token, never the token."""

    return hmac.new(token.encode(), b"aistack-setup-form", sha256).hexdigest()[:32]


def new_token(generated: Path, *, reopen: bool = False) -> str:
    """A new token, replacing any other; `reopen` opens a finished assistant again."""

    directory = folder(generated)
    directory.mkdir(parents=True, exist_ok=True)
    if reopen:
        (directory / FINISHED_FILE).unlink(missing_ok=True)
    elif finished(generated):
        raise ValueError("the installation assistant is finished: reopen it to make a new token")
    token = secrets.token_hex(24)
    _write_private(directory / TOKEN_FILE, token + "\n")
    return token


def finish(generated: Path, when: datetime) -> None:
    directory = folder(generated)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / FINISHED_FILE).write_text(when.isoformat(timespec="seconds") + "\n", encoding="utf-8")
    (directory / TOKEN_FILE).unlink(missing_ok=True)


def _write_private(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
    temporary.replace(path)


# --------------------------------------------------------------------
# install.sh's answers, and the steps saved
# --------------------------------------------------------------------


def install_answers(generated: Path) -> dict[str, str]:
    try:
        lines = (folder(generated) / ANSWERS_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    answers = {}
    for line in lines:
        name, separator, value = line.partition("=")
        if separator and name.strip() in ANSWER_KEYS:
            answers[name.strip()] = value.strip()
    return answers


def progress(generated: Path) -> dict[int, str]:
    """Each step saved, and when."""

    try:
        data = json.loads((folder(generated) / PROGRESS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {int(step): str(when) for step, when in data.items() if str(step).isdigit()}


def mark_saved(generated: Path, step: int, when: datetime) -> None:
    saved = progress(generated)
    saved[step] = when.isoformat(timespec="seconds")
    directory = folder(generated)
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps({str(key): value for key, value in sorted(saved.items())}, indent=2) + "\n"
    temporary = directory / f".{PROGRESS_FILE}.{os.getpid()}"
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(directory / PROGRESS_FILE)


def choices(generated: Path) -> dict[str, str]:
    """What a step asked that no declaration holds (the reverse proxy, the domain)."""

    try:
        data = json.loads((folder(generated) / CHOICES_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(key): str(value) for key, value in data.items()} if isinstance(data, dict) else {}


def remember(generated: Path, **values: str) -> None:
    kept = choices(generated) | values
    directory = folder(generated)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f".{CHOICES_FILE}.{os.getpid()}"
    temporary.write_text(json.dumps(kept, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(directory / CHOICES_FILE)


# --------------------------------------------------------------------
# Writing a declaration
# --------------------------------------------------------------------


def _header(name: str, when: datetime) -> str:
    return (
        f"# AIStack — {name}, written by the installation assistant (/setup,\n"
        f"# ADR-0023 § 5) on {when.date().isoformat()}. Yours to edit from now on:\n"
        "# AIStack reads it again when it restarts.\n\n"
    )


def read_declaration(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping")
    return data


def write_declaration(directory: Path, name: str, data: Mapping[str, Any], when: datetime) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    text = _header(name, when) + yaml.safe_dump(dict(data), sort_keys=False, allow_unicode=True)
    temporary = directory / f".{name}.{os.getpid()}"
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(target)
    return target


def host_name_error(value: str) -> bool:
    return not _HOST_NAME.match(value)


def clean_name(value: str) -> str:
    """`https://aistack.example.org/` → `aistack.example.org`."""

    value = value.strip().lower()
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.rstrip("/")


# --------------------------------------------------------------------
# Step 1 — the host
# --------------------------------------------------------------------


@dataclass(frozen=True)
class HostAnswer:
    lan_hostname: str
    console_port: int
    web_lan_port: int
    phase: str


def parse_host(lan_hostname: str, console_port: str, web_lan_port: str, phase: str) -> tuple[HostAnswer | None, list[str]]:
    """The answer, or what is wrong with it: catalog keys under `setup.error.`."""

    errors = []
    name = lan_hostname.strip()
    if host_name_error(name):
        errors.append("host_name")
    ports = []
    for value in (console_port, web_lan_port):
        try:
            port = int(value.strip())
        except ValueError:
            port = 0
        ports.append(port)
    if any(not 1024 <= port <= 65535 for port in ports):
        errors.append("port_range")
    elif ports[0] == ports[1]:
        errors.append("port_same")
    if phase not in PHASES:
        errors.append("phase")
    if errors:
        return None, errors
    return HostAnswer(name, ports[0], ports[1], phase), []


def host_declaration(current: Mapping[str, Any], answer: HostAnswer) -> dict[str, Any]:
    data = dict(current)
    ports = dict(data.get("service_ports") or {})
    ports["console"] = answer.console_port
    ports["web_lan"] = answer.web_lan_port
    data["lan_hostname"] = answer.lan_hostname
    data["service_ports"] = ports
    data["phase"] = answer.phase
    return data


# --------------------------------------------------------------------
# Step 2 — the public address
# --------------------------------------------------------------------


@dataclass(frozen=True)
class PublicAnswer:
    domain: str
    proxy: str
    aistack_name: str
    id_name: str

    @property
    def public_base_url(self) -> str:
        return f"https://{self.aistack_name}"

    @property
    def issuer(self) -> str:
        return f"https://{self.id_name}"


def parse_public(domain: str, proxy: str, aistack_name: str, id_name: str) -> tuple[PublicAnswer | None, list[str]]:
    errors = []
    domain = clean_name(domain)
    if host_name_error(domain) or "." not in domain:
        errors.append("domain")
    aistack = clean_name(aistack_name) or (f"aistack.{domain}" if domain else "")
    identity = clean_name(id_name) or (f"id.{domain}" if domain else "")
    for value, key in ((aistack, "aistack_name"), (identity, "id_name")):
        if not value or host_name_error(value) or "." not in value:
            errors.append(key)
    if aistack and aistack == identity:
        errors.append("names_same")
    if proxy not in PROXIES:
        errors.append("proxy")
    if errors:
        return None, errors
    return PublicAnswer(domain, proxy, aistack, identity), []


def public_declaration(current: Mapping[str, Any], answer: PublicAnswer) -> dict[str, Any]:
    data = dict(current)
    data["issuer"] = answer.issuer
    data["public_base_url"] = answer.public_base_url
    return data


@dataclass(frozen=True)
class Probe:
    """What an address answered: the HTTP status (None when nothing
    answered), the start of the body, why it failed."""

    status: int | None
    body: str = ""
    reason: str = ""


def probe(url: str, timeout: float = 8.0) -> Probe:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "AIStack installation assistant"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 — https only, typed by the person
            return Probe(int(response.status), response.read(65536).decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as error:
        return Probe(int(error.code), "", str(error.reason))
    except (urllib.error.URLError, OSError, ValueError) as error:
        reason = getattr(error, "reason", error)
        return Probe(None, "", str(reason))


@dataclass(frozen=True)
class Check:
    """One address asked: `ok`, and the reason shown when it is not."""

    url: str
    ok: bool
    detail: str


def check_aistack(answer: PublicAnswer, ask: Any = probe) -> Check:
    url = answer.public_base_url + "/console.html"
    found: Probe = ask(url)
    if found.status == 200 and "AIStack" in found.body:
        return Check(url, True, "200")
    if found.status is None:
        return Check(url, False, found.reason)
    return Check(url, False, f"HTTP {found.status} {found.reason}".strip())


def check_pocket_id(answer: PublicAnswer, ask: Any = probe) -> Check:
    url = answer.issuer + "/.well-known/openid-configuration"
    found: Probe = ask(url)
    if found.status != 200:
        return Check(url, False, found.reason if found.status is None else f"HTTP {found.status} {found.reason}".strip())
    try:
        issuer = json.loads(found.body).get("issuer")
    except (ValueError, AttributeError):
        return Check(url, False, "not an OpenID Connect discovery document")
    if issuer != answer.issuer:
        return Check(url, False, f"issuer = {issuer}")
    return Check(url, True, "200")
