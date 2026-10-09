"""API keys entered from Settings (2026-10-09): the store, the overlay on the environment, what is shown."""

from __future__ import annotations

import stat
from pathlib import Path

from aistack import api_keys
from aistack.api_keys import ApiKey, apply_to_environ, load_api_keys, state, write_value

GEMINI = ApiKey("AISTACK_GEMINI_API_KEY", {"fr": "Gemini"}, {}, {})
URL = ApiKey("AISTACK_GOTIFY_URL", {"fr": "Gotify"}, {}, {}, secret=False)


def test_every_shipped_key_is_declared_with_its_texts():
    keys = load_api_keys()
    names = [key.name for key in keys]
    assert "AISTACK_GEMINI_API_KEY" in names and "SYNCTHING_API_KEY" in names and "JELLYFIN_API_KEY" in names
    assert "AISTACK_OIDC_CLIENT_SECRET" not in names
    assert all(key.text(key.title, "fr") and key.text(key.title, "en") for key in keys)


def test_a_value_is_kept_readable_by_aistack_only(tmp_path: Path):
    write_value(tmp_path, GEMINI.name, "abcdefgh-1234")

    path = tmp_path / api_keys.STORE
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert api_keys.read_store(tmp_path) == {GEMINI.name: "abcdefgh-1234"}


def test_settings_win_over_the_env_file_and_clearing_gives_it_back(tmp_path: Path):
    env = {GEMINI.name: "from-env-file-9999"}
    write_value(tmp_path, GEMINI.name, "from-settings-1234")

    apply_to_environ(tmp_path, [GEMINI], env)
    assert env[GEMINI.name] == "from-settings-1234"
    assert state(GEMINI, tmp_path, env) == (api_keys.FROM_SETTINGS, "…1234")

    write_value(tmp_path, GEMINI.name, None)
    apply_to_environ(tmp_path, [GEMINI], env)
    assert env[GEMINI.name] == "from-env-file-9999"
    assert state(GEMINI, tmp_path, env) == (api_keys.FROM_ENV_FILE, "…9999")


def test_a_key_set_nowhere_is_absent_and_cleared_is_removed(tmp_path: Path):
    env: dict[str, str] = {}
    assert state(GEMINI, tmp_path, env) == (api_keys.ABSENT, "")
    write_value(tmp_path, GEMINI.name, "only-in-settings-5678")
    apply_to_environ(tmp_path, [GEMINI], env)
    write_value(tmp_path, GEMINI.name, None)
    apply_to_environ(tmp_path, [GEMINI], env)
    assert GEMINI.name not in env


def test_a_short_secret_shows_nothing_and_an_address_shows_in_full(tmp_path: Path):
    write_value(tmp_path, GEMINI.name, "short")
    write_value(tmp_path, URL.name, "https://gotify.example")
    assert state(GEMINI, tmp_path, {}) == (api_keys.FROM_SETTINGS, "…")
    assert state(URL, tmp_path, {}) == (api_keys.FROM_SETTINGS, "https://gotify.example")
