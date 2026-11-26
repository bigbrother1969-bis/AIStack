"""
What expires, read (ADR-0032, slice O7): the certificates the owner serves and the domains the owner rents.

A certificate is read where it lives: a host name (`host` or `host:port`) is asked for the certificate it presents, and an
absolute path is a PEM file (a wildcard certificate a reverse proxy keeps in a folder). A domain is read from its registry's
RDAP service, the public successor of whois; a registry that does not publish an expiry (some country domains do not) is
*not read*, and the owner may declare the date by hand for it. A reading that failed says why and is never a good date.

Read-only: one TLS handshake per host, one GET per domain, one file. Nothing is written, and the certificate's subject, its
issuer and its serial number never leave this module: only when it ends. A domain is asked at most twice a day.
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from cryptography import x509

USER_AGENT = "AIStack-BootChecks/1.0"
TLS_TIMEOUT = 8
RDAP_TIMEOUT = 15
RDAP_URL = "https://rdap.org/domain/{}"
# A registry is asked about a domain at most this often; a failed answer is asked again sooner.
KEEP_SECONDS = 12 * 3600
RETRY_SECONDS = 3600
# What the library says when a certificate is past its date: the date is judged by the control, not the handshake.
EXPIRED_CODE = 10

HOST = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?(?::\d{1,5})?$")
DOMAIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
_EVENT_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})")

_ANSWERS: dict[str, tuple[float, "Expiry"]] = {}


@dataclass(frozen=True)
class Expiry:
    """
    When one thing ends. `ends` is `None` when it could not be read (`reason` says why); `problem` is set for a certificate
    that was read but is not to be trusted (another name, a chain that does not lead to a known authority).
    """

    name: str
    ends: datetime | None
    reason: str = ""
    problem: str = ""


@dataclass(frozen=True)
class ExpiryReading:
    certificates: tuple[Expiry, ...] = ()
    domains: tuple[Expiry, ...] = ()


def _why(error: BaseException) -> str:
    text = getattr(error, "reason", None) or str(error) or type(error).__name__

    return str(text).replace("\n", " ")[:80]


def certificate_file(path: str) -> Expiry:
    """When a PEM certificate file ends (the first certificate of a chain file is the one served)."""

    try:
        data = Path(path).read_bytes()
    except OSError as error:
        return Expiry(path, None, _why(error))

    try:
        return Expiry(path, x509.load_pem_x509_certificate(data).not_valid_after_utc)
    except ValueError:
        return Expiry(path, None, "not a PEM certificate")


def _handshake(host: str, port: int, timeout: float, verify: bool) -> bytes:
    context = ssl.create_default_context()

    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host, port), timeout=timeout) as raw, context.wrap_socket(raw, server_hostname=host) as tls:
        der = tls.getpeercert(binary_form=True)

    if not der:
        raise OSError("no certificate presented")

    return der


def certificate_host(entry: str, timeout: float = TLS_TIMEOUT) -> Expiry:
    """When the certificate a host presents ends, and whether it would be trusted (name and chain)."""

    host, _, port = entry.partition(":")
    problem = ""

    try:
        der = _handshake(host, int(port or 443), timeout, True)
    except ssl.SSLCertVerificationError as error:
        problem = "" if error.verify_code == EXPIRED_CODE else str(error.verify_message or "not trusted")[:80]

        try:
            der = _handshake(host, int(port or 443), timeout, False)
        except (OSError, ValueError) as again:
            return Expiry(entry, None, _why(again))
    except (OSError, ValueError) as error:
        return Expiry(entry, None, _why(error))

    try:
        return Expiry(entry, x509.load_der_x509_certificate(der).not_valid_after_utc, problem=problem)
    except ValueError:
        return Expiry(entry, None, "not a certificate")


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"Accept": "application/rdap+json, application/json", "User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=RDAP_TIMEOUT) as answer:  # noqa: S310 - the scheme is fixed above
        return str(answer.read(1_000_000).decode("utf-8", "replace"))


def parse_rdap(text: str) -> datetime | None:
    """The `expiration` event of an RDAP answer, in UTC; `None` when the answer carries none."""

    try:
        events = json.loads(text).get("events", [])
    except (ValueError, AttributeError):
        return None

    for event in events if isinstance(events, list) else ():
        if isinstance(event, dict) and event.get("eventAction") == "expiration":
            found = _EVENT_DATE.match(str(event.get("eventDate", "")))

            if found is not None:
                year, month, day, hour, minute, second = (int(part) for part in found.groups())

                return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

    return None


def domain_expiry(name: str, declared: str = "", fetch: Callable[[str], str] = _get) -> Expiry:
    """
    When a domain ends, from its registry. A registry that publishes nothing falls back on the date the owner declared
    (`YYYY-MM-DD`), and with neither the domain is not read. Answers are kept (`KEEP_SECONDS`) so the registry is not asked
    at every pass.
    """

    kept = _ANSWERS.get(name)

    if kept is not None and time.monotonic() < kept[0]:
        return kept[1]

    try:
        ends = parse_rdap(fetch(RDAP_URL.format(name)))
        reason = "the registry does not publish the expiry (RDAP)"
    except urllib.error.HTTPError as error:
        ends, reason = None, f"the registry does not answer for this domain (HTTP {error.code})"
    except (OSError, ValueError) as error:
        ends, reason = None, f"the registry did not answer ({_why(error)})"

    if ends is None and declared:
        day = date.fromisoformat(declared)
        found = Expiry(name, datetime(day.year, day.month, day.day, 23, 59, tzinfo=timezone.utc))
    elif ends is None:
        found = Expiry(name, None, reason)
    else:
        found = Expiry(name, ends)

    _ANSWERS[name] = (time.monotonic() + (KEEP_SECONDS if found.ends is not None else RETRY_SECONDS), found)

    return found


def read_expiries(
    certificates: tuple[str, ...],
    domains: dict[str, str],
    *,
    host: Callable[[str], Expiry] = certificate_host,
    file: Callable[[str], Expiry] = certificate_file,
    domain: Callable[[str, str], Expiry] = domain_expiry,
) -> ExpiryReading:
    """Everything the owner declared, each read on its own: one that fails does not stop the others."""

    return ExpiryReading(
        tuple(file(entry) if entry.startswith("/") else host(entry) for entry in certificates),
        tuple(domain(name, declared) for name, declared in sorted(domains.items())),
    )
