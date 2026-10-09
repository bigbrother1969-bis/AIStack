"""
Syncthing's configuration, read and — on the owner's click only —
added to (`ADR-0022` § 5): the devices paired with this host, whether a
folder exists, and a new send-only folder shared with one device.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from aistack.sync.declaration import SyncthingAccess, api_key

Call = Callable[[str, str, bytes | None], Any]


class SyncthingRefused(OSError):
    """Syncthing did not answer, or refused."""


def _call(url: str, key: str, timeout: float) -> Call:
    def call(method: str, path: str, body: bytes | None) -> Any:
        request = urllib.request.Request(
            url + path,
            data=body,
            method=method,
            headers={"X-API-Key": key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as answer:  # noqa: S310 — this host's own Syncthing
                text = answer.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raise SyncthingRefused(f"HTTP {error.code} on {path}: {error.read(200).decode('utf-8', 'replace')}") from None
        except (urllib.error.URLError, OSError) as error:
            raise SyncthingRefused(f"{url}: {error}") from None
        return json.loads(text) if text.strip() else None

    return call


@dataclass
class SyncthingConfig:
    call: Call

    @staticmethod
    def of(access: SyncthingAccess) -> "SyncthingConfig":
        return SyncthingConfig(_call(access.url, api_key(access), access.timeout_seconds))

    def devices(self) -> list[dict[str, Any]]:
        return list(self.call("GET", "/rest/config/devices", None) or [])

    def device_id(self, name_or_id: str) -> str:
        """The full id of a device named, or given by its id or the start of it."""

        for device in self.devices():
            ident = str(device.get("deviceID", ""))
            if name_or_id in (ident, device.get("name")) or (len(name_or_id) >= 7 and ident.startswith(name_or_id)):
                return ident
        raise SyncthingRefused(f"no device `{name_or_id}` paired with this Syncthing")

    def folder(self, folder_id: str) -> dict[str, Any] | None:
        for folder in self.call("GET", "/rest/config/folders", None) or []:
            if folder.get("id") == folder_id:
                return dict(folder)
        return None

    def reshare(self, folder_id: str, device_id: str) -> None:
        """
        Offer the folder to the device again: the device is taken off
        the folder's list and put back, so Syncthing sends it a new
        offer at its next connection (the owner, 2026-10-09: the phone
        missed the first one). A folder ignored on the device itself
        stays ignored until it is un-ignored there.
        """

        from urllib.parse import quote

        folder = self.folder(folder_id)
        if folder is None:
            raise SyncthingRefused(f"no folder `{folder_id}` in this Syncthing")
        path = f"/rest/config/folders/{quote(folder_id, safe='')}"
        others = [d for d in folder.get("devices") or [] if d.get("deviceID") != device_id]
        self.call("PUT", path, json.dumps({**folder, "devices": others}).encode("utf-8"))
        self.call("PUT", path, json.dumps({**folder, "devices": [*others, {"deviceID": device_id}]}).encode("utf-8"))

    def add_folder(self, folder_id: str, label: str, path: str, device_id: str) -> None:
        """A send-only folder (one way, `ADR-0022` § 3), shared with one device."""

        body = {
            "id": folder_id,
            "label": label,
            "path": path,
            "type": "sendonly",
            "devices": [{"deviceID": device_id}],
        }
        self.call("POST", "/rest/config/folders", json.dumps(body).encode("utf-8"))
