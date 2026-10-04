"""
`authentication.yml` — how a person signs in (`ADR-0013` § 2, § 3).
"""

from __future__ import annotations

from aistack.config import configured

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_DEFINITION = configured(Path(__file__).resolve().parent / "definitions" / "authentication.yml")

CALLBACK_PATH = "/auth/callback"
AFTER_LOGOUT_PATH = "/console.html"


@dataclass(frozen=True)
class AuthenticationDefinition:
    issuer: str
    public_base_url: str
    scopes: tuple[str, ...]
    client_id_env: str
    client_secret_env: str
    local_admin_env: str
    admin_group: str
    session_idle_hours: float
    session_absolute_days: float

    @property
    def redirect_uri(self) -> str:
        return self.public_base_url + CALLBACK_PATH

    @property
    def after_logout_uri(self) -> str:
        return self.public_base_url + AFTER_LOGOUT_PATH

    def redirect_uri_for(self, base_url: str) -> str:
        """The callback on another listener (ADR-0014 § 4)."""

        return base_url + CALLBACK_PATH

    def after_logout_uri_for(self, base_url: str) -> str:
        return base_url + AFTER_LOGOUT_PATH


@dataclass(frozen=True)
class Credentials:
    """What `.env.web` holds for sign-in; an empty value is absent."""

    client_id: str
    client_secret: str
    local_admin_hash: str

    @property
    def oidc_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


def load_authentication_yaml(path: Path = DEFAULT_DEFINITION) -> AuthenticationDefinition:
    with path.open("r", encoding="utf-8") as stream:
        data: Any = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a mapping")

    for field in ("issuer", "public_base_url"):
        value = str(data.get(field) or "")
        if not value.startswith("https://") or value.endswith("/"):
            raise ValueError(f"{path}: {field} must be an https:// address without a trailing /")

    scopes = tuple(str(scope) for scope in data.get("scopes") or ())
    if "openid" not in scopes:
        raise ValueError(f"{path}: scopes must include openid")

    return AuthenticationDefinition(
        issuer=str(data["issuer"]),
        public_base_url=str(data["public_base_url"]),
        scopes=scopes,
        client_id_env=str(data["client_id_env"]),
        client_secret_env=str(data["client_secret_env"]),
        local_admin_env=str(data["local_admin_env"]),
        admin_group=str(data["admin_group"]),
        session_idle_hours=float(data["session_idle_hours"]),
        session_absolute_days=float(data["session_absolute_days"]),
    )


def credentials_from(environment: Mapping[str, str], definition: AuthenticationDefinition) -> Credentials:
    return Credentials(
        client_id=environment.get(definition.client_id_env, "").strip(),
        client_secret=environment.get(definition.client_secret_env, "").strip(),
        local_admin_hash=environment.get(definition.local_admin_env, "").strip(),
    )
