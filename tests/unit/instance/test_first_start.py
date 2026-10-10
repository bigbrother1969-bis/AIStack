"""What a new installation still has to declare (ADR-0017 § 4)."""

from __future__ import annotations

from pathlib import Path

from aistack.cli.config_init import init
from aistack.instance.first_start import (
    AUTHENTICATION,
    FALLBACK_SECRET,
    INSTANCE,
    SHIPPED_RECORD,
    SIGN_IN_SECRETS,
    needs_setup,
    pending,
    still_shipped,
)

SECRETS = {"client_id": "id", "client_secret": "secret", "local_admin_hash": "scrypt$1"}


def keys(directory: Path | None, **secrets: str) -> list[str]:
    return [item.key for item in pending(directory, **{**SECRETS, **secrets})]


def test_a_fresh_directory_still_holds_the_reference_host_s_instance_and_provider(tmp_path: Path):
    init(tmp_path)

    assert keys(tmp_path) == [INSTANCE, AUTHENTICATION]
    assert (tmp_path / SHIPPED_RECORD).is_file()


def test_an_edited_declaration_is_no_longer_reported(tmp_path: Path):
    init(tmp_path)
    path = tmp_path / "instance_config.yml"
    path.write_text(path.read_text(encoding="utf-8").replace("lan_hostname: localhost", "lan_hostname: ELSEWHERE"), encoding="utf-8")

    assert not still_shipped(tmp_path, "instance_config.yml")
    assert keys(tmp_path) == [AUTHENTICATION]


def test_a_file_the_owner_put_there_is_never_reported_even_with_the_shipped_values(tmp_path: Path):
    """GIGABYTE's own files, at its move, are the shipped values: they
    were placed, not copied."""

    from aistack.config import shipped_definitions

    for shipped in shipped_definitions():
        if shipped.name in ("instance_config.yml", "authentication.yml"):
            (tmp_path / shipped.name).write_bytes(shipped.read_bytes())
    init(tmp_path)

    assert keys(tmp_path) == []


def test_a_second_start_keeps_what_the_first_one_recorded(tmp_path: Path):
    init(tmp_path)
    init(tmp_path)

    assert keys(tmp_path) == [INSTANCE, AUTHENTICATION]


def test_without_a_configuration_directory_only_the_secrets_are_checked():
    assert keys(None) == []
    assert keys(None, client_secret="") == [SIGN_IN_SECRETS]
    assert keys(None, local_admin_hash="") == [FALLBACK_SECRET]


def test_the_fallback_account_is_recommended_not_required():
    assert not needs_setup(pending(None, **{**SECRETS, "local_admin_hash": ""}))
    assert needs_setup(pending(None, **{**SECRETS, "client_id": ""}))


def test_an_unreadable_record_reports_nothing_as_shipped(tmp_path: Path):
    init(tmp_path)
    (tmp_path / SHIPPED_RECORD).write_text("not json", encoding="utf-8")

    assert keys(tmp_path) == []
