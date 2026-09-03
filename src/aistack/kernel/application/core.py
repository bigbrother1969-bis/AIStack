from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncthingDefinition:
    """
    Where a Selection UI instance reaches Syncthing.

    **`api_key_env` names an environment variable; it is never the
    key.** "Aucun secret ne passe par toi. Il s'authentifie
    lui-même" — the owner's own words, 2026-08-29. A governed
    artifact is read by whoever has the repository, and the key is
    not for whoever has the repository, so this class carries the
    name of where to look, never the value found there.
    """

    url: str
    folder_id: str
    device_id: str = ""
    api_key_env: str = ""
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ApplicationDefinition:
    """
    What one Selection UI instance is, named rather than written into code.

    Decision of 2026-08-29: this screen is the first of a family.
    Until now `source_root`, `target_root`, the Syncthing folder
    and device, and the declared capacity lived as literals inside
    `selection_ui/app.py` — some of them, like the declared quota
    and the phone's device identifier, did not exist as a concept
    in the code at all. A second instance of the family should
    differ only by which YAML it is handed.

    **`source_root` and `target_root` are real filesystem paths,
    not repository-relative ones.** The library they name lives on
    the host the app runs on — GIGABYTE, decided 2026-08-29 — never
    inside this repository, unlike `selection_file`, which is a
    governed artefact and stays repository-relative like the
    catalog and selection stores it sits beside.

    **`capacity_declared_bytes` follows `assess_capacity`'s own
    convention.** Zero or absent reads as *not declared*, never as
    a quota of zero that would refuse everything — the definition
    is written by hand, and an absent line and a line reading `0`
    are the same accident.
    """

    app_id: str
    title: str
    view_id: str
    source_root: str
    target_root: str
    selection_file: str
    capacity_declared_bytes: int = 0
    syncthing: SyncthingDefinition | None = None

    @property
    def catalog_id(self) -> str:
        """
        Derived, not asked twice.

        Nothing in this family varies a catalog's identifier
        independently of the app that produces it, so the
        definition does not make a human write `music_android` a
        second time under a different key.
        """

        return f"{self.app_id}-library"

    @property
    def catalog_title(self) -> str:
        return f"{self.title} — Library"
