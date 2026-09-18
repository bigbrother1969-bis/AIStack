from __future__ import annotations

import base64
import hashlib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

_DAV_NS = "DAV:"

# The `_PROPFIND_BODY` asks for exactly the four properties P2 needs
# to recoup a file's identity without a second call: size and etag
# to verify it arrived intact, `getlastmodified` to place it in time,
# `resourcetype` to tell a file from a subfolder. WebDAV servers
# answer whatever is asked and nothing else — asking for less than
# this would silently under-report; asking for more would carry
# fields nothing here reads.
_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8" ?>'
    '<d:propfind xmlns:d="DAV:">'
    "<d:prop>"
    "<d:getcontentlength/>"
    "<d:getetag/>"
    "<d:getlastmodified/>"
    "<d:resourcetype/>"
    "</d:prop>"
    "</d:propfind>"
).encode("utf-8")


class NextcloudProvider:
    """
    Observe what one Nextcloud folder holds, for one account.

    A provider observes and does not qualify (ARC-P-012, the same
    boundary `DockerProvider.collect_logs` documents): this reports
    what WebDAV answered, never whether a file is "safe" — P2 (the
    verification step) is what compares this against what a Shortcut
    claims to have sent, and only P2 draws a conclusion from it.

    **`PROPFIND`, not the REST API a Nextcloud app would use.** The
    thing that will write into this folder is an iOS Shortcut talking
    raw HTTP, not the Nextcloud app — reading it back the same way,
    over WebDAV (`FDN-0004`: Nextcloud is a Knowledge Provider here,
    never a Kernel concept), keeps this provider honest about what a
    plain WebDAV client actually sees, rather than a view privileged
    by a client library.

    **A missing folder is not an error.** `PLAN-PHOTOS-IPHONE-
    NEXTCLOUD-IMMICH-2026-09-18.md` names the target as a brand-new
    subfolder nothing has written to yet on a fresh install. A `404`
    there is the ordinary first-run state, not a fault — `reachable`
    stays `True` and `folder_exists` says `False`, the same
    distinction `SyncthingProvider` draws between an unreachable
    daemon and a folder that answered without every field.

    **The app password travels in the `Authorization` header and
    nowhere else** — the same discipline `SyncthingProvider` holds
    for its API key: it never enters the query string, where a
    reverse proxy's access log would keep it.
    """

    provider_id = "aistack.provider.nextcloud"
    provider_name = "Nextcloud Provider"

    def __init__(
        self,
        url: str,
        username: str,
        app_password: str,
        folder: str,
        timeout: float = 5.0,
    ) -> None:
        self.url = url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self.folder = folder.strip("/")
        self.timeout = timeout

    def collect(self) -> dict[str, Any]:
        observation: dict[str, Any] = {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "nextcloud": {
                "url": self.url,
                "username": self.username,
                "folder": self.folder,
                "reachable": False,
                "unreachable_reason": "",
                "folder_exists": False,
                "files": [],
            },
        }

        state = observation["nextcloud"]

        if not self.app_password:
            state["unreachable_reason"] = (
                "no app password was provided, so Nextcloud was not asked"
            )
            return observation

        files, exists, reason = self._propfind()

        if reason:
            state["unreachable_reason"] = reason
            return observation

        state["reachable"] = True
        state["folder_exists"] = exists
        state["files"] = files

        return observation

    def download(self, name: str) -> dict[str, Any]:
        """
        Fetch one file's actual bytes and hash them — a second,
        independent observation of the same file `collect()` already
        described from `PROPFIND`'s metadata.

        This is still collection, not qualification (`ARC-P-012`):
        it reports what a `GET` returned and what was computed from
        it, never whether that makes the upload "safe". P2
        (`aistack.providers.nextcloud.verify.verify_uploads`) is what
        compares this against the `PROPFIND` observation and decides.

        The `sha256` is reported for the audit trail even though
        nothing yet exists to compare it against — there is no
        independent copy of the original file this provider can
        reach (the phone's own copy is outside AIStack entirely) — so
        today's recoupment is the size agreement between two separate
        requests, `PROPFIND` and `GET`, not a content-hash match.
        """

        if not self.app_password:
            return self._download_failure(
                name,
                "no app password was provided, so Nextcloud was not asked",
            )

        path = self._file_path(name)

        request = urllib.request.Request(
            f"{self.url}{path}",
            method="GET",
            headers={"Authorization": self._authorization_header()},
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                hasher = hashlib.sha256()
                downloaded_size = 0

                while True:
                    chunk = response.read(65536)

                    if not chunk:
                        break

                    hasher.update(chunk)
                    downloaded_size += len(chunk)

        except TimeoutError:
            return self._download_failure(name, self._timed_out())

        except urllib.error.HTTPError as error:
            return self._download_failure(
                name,
                f"Nextcloud refused GET {path} with status "
                f"{error.code} ({error.reason})",
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return self._download_failure(name, self._timed_out())

            return self._download_failure(
                name,
                f"Nextcloud at {self.url} could not be reached: "
                f"{error.reason}",
            )

        except OSError as error:
            return self._download_failure(
                name,
                f"Nextcloud answered GET with something unreadable: "
                f"{error}",
            )

        return {
            "name": name,
            "downloaded": True,
            "reason": "",
            "downloaded_size": downloaded_size,
            "sha256": hasher.hexdigest(),
        }

    @staticmethod
    def _download_failure(name: str, reason: str) -> dict[str, Any]:
        return {
            "name": name,
            "downloaded": False,
            "reason": reason,
            "downloaded_size": None,
            "sha256": None,
        }

    def _file_path(self, name: str) -> str:
        return (
            "/remote.php/dav/files/"
            + urllib.parse.quote(self.username)
            + "/"
            + urllib.parse.quote(self.folder)
            + "/"
            + urllib.parse.quote(name)
        )

    def _authorization_header(self) -> str:
        credentials = base64.b64encode(
            f"{self.username}:{self.app_password}".encode()
        ).decode()
        return f"Basic {credentials}"

    def _propfind(self) -> tuple[list[dict[str, Any]], bool, str]:
        path = (
            "/remote.php/dav/files/"
            + urllib.parse.quote(self.username)
            + "/"
            + urllib.parse.quote(self.folder)
        )

        request = urllib.request.Request(
            f"{self.url}{path}",
            data=_PROPFIND_BODY,
            method="PROPFIND",
            headers={
                "Authorization": self._authorization_header(),
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                payload = response.read()

        except TimeoutError:
            return [], False, self._timed_out()

        except urllib.error.HTTPError as error:

            if error.code == 404:
                # Nothing has been uploaded into this folder yet —
                # the ordinary state of a subfolder a Shortcut has
                # not written to for the first time, not a fault.
                return [], False, ""

            return [], False, (
                f"Nextcloud refused PROPFIND {path} with status "
                f"{error.code} ({error.reason})"
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return [], False, self._timed_out()

            return [], False, (
                f"Nextcloud at {self.url} could not be reached: "
                f"{error.reason}"
            )

        except OSError as error:
            return [], False, (
                f"Nextcloud answered PROPFIND with something unreadable: "
                f"{error}"
            )

        try:
            files = self._parse_multistatus(payload, path)
        except ElementTree.ParseError as error:
            return [], False, (
                f"Nextcloud answered PROPFIND with unparsable XML: {error}"
            )

        return files, True, ""

    def _parse_multistatus(
        self, payload: bytes, requested_path: str
    ) -> list[dict[str, Any]]:
        """
        One `<d:response>` per resource, the queried folder included.

        The folder answers about itself first, in the same list as
        its children (WebDAV `Depth: 1`) — that entry is excluded
        here rather than left for a caller to notice it is not a
        file. Subfolders are excluded the same way, by
        `resourcetype`, not by guessing from the name.
        """

        root = ElementTree.fromstring(payload)
        requested = urllib.parse.unquote(requested_path).rstrip("/")
        files: list[dict[str, Any]] = []

        for response in root.findall(f"{{{_DAV_NS}}}response"):
            href_element = response.find(f"{{{_DAV_NS}}}href")

            if href_element is None or not href_element.text:
                continue

            href = urllib.parse.unquote(href_element.text).rstrip("/")

            if href == requested:
                continue

            prop = self._ok_prop(response)

            if prop is None:
                continue

            resourcetype = prop.find(f"{{{_DAV_NS}}}resourcetype")

            if resourcetype is not None and (
                resourcetype.find(f"{{{_DAV_NS}}}collection") is not None
            ):
                continue

            files.append(self._file_entry(href, prop))

        return files

    @staticmethod
    def _ok_prop(response: ElementTree.Element) -> ElementTree.Element | None:
        """
        WebDAV answers each property in its own `propstat`, grouped
        by status — a server that does not know `resourcetype` still
        answers `200` for the properties it does know. Only the `200`
        group is a fact; the rest is what the server declined.
        """

        for propstat in response.findall(f"{{{_DAV_NS}}}propstat"):
            status = propstat.find(f"{{{_DAV_NS}}}status")

            if status is not None and status.text and " 200 " in status.text:
                return propstat.find(f"{{{_DAV_NS}}}prop")

        return None

    @staticmethod
    def _file_entry(
        href: str, prop: ElementTree.Element
    ) -> dict[str, Any]:
        size_element = prop.find(f"{{{_DAV_NS}}}getcontentlength")
        etag_element = prop.find(f"{{{_DAV_NS}}}getetag")
        modified_element = prop.find(f"{{{_DAV_NS}}}getlastmodified")

        size = None

        if size_element is not None and size_element.text:
            size = int(size_element.text)

        etag = None

        if etag_element is not None and etag_element.text:
            etag = etag_element.text.strip('"')

        last_modified = None

        if modified_element is not None and modified_element.text:
            last_modified = modified_element.text

        return {
            "name": href.rsplit("/", 1)[-1],
            "size": size,
            "etag": etag,
            "last_modified": last_modified,
        }

    def _timed_out(self) -> str:
        return (
            f"Nextcloud at {self.url} did not answer within "
            f"{self.timeout} seconds"
        )
