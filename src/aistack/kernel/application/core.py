from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncthingDefinition:
    """
    Where a Selection UI instance reaches Syncthing.

    `api_key_env` names an environment variable, never the key itself:
    definitions are readable by anyone with the repository.
    """

    url: str
    folder_id: str
    device_id: str = ""
    api_key_env: str = ""
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ApplicationDefinition:
    """
    What one Selection UI instance is, declared in YAML rather than code;
    instances differ only by their YAML.

    `source_root` and `target_root` are absolute filesystem paths on the
    host; `selection_file` is repository-relative. A
    `capacity_declared_bytes` of zero means not declared, never a quota
    of zero (as in `assess_capacity`).
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
        """The catalog identifier, derived from `app_id`."""

        return f"{self.app_id}-library"

    @property
    def catalog_title(self) -> str:
        return f"{self.title} — Library"
