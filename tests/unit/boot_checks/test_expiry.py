"""What expires: the certificates served and the domains rented, read and judged (O7)."""

from __future__ import annotations

import datetime as dt
import json
import ssl
import threading
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from aistack.boot_checks import expiry
from aistack.boot_checks.controls import OK, SKIPPED, UNKNOWN, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.expiry import Expiry, ExpiryReading
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.phrases import say
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import facts

NOW = datetime(2026, 11, 26, 21, 0, tzinfo=timezone.utc)


def make_certificate(directory: Path, ends: datetime, name: str = "localhost") -> tuple[Path, Path]:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ends - timedelta(days=90))
        .not_valid_after(ends)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    pem = directory / "fullchain.pem"
    private = directory / "key.pem"
    pem.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))

    return pem, private


def test_a_certificate_file_says_when_it_ends_and_nothing_else(tmp_path: Path) -> None:
    pem, _ = make_certificate(tmp_path, datetime(2027, 1, 23, 19, 10, 54, tzinfo=timezone.utc), "secret-name.example")
    found = expiry.certificate_file(str(pem))

    assert found == Expiry(str(pem), datetime(2027, 1, 23, 19, 10, 54, tzinfo=timezone.utc))
    assert "secret-name" not in repr(found)


def test_a_file_that_is_not_a_certificate_or_not_there_is_not_read() -> None:
    assert expiry.certificate_file("/nowhere/x.pem").ends is None and expiry.certificate_file("/nowhere/x.pem").reason


def test_a_file_that_is_not_pem_says_so(tmp_path: Path) -> None:
    (tmp_path / "x.pem").write_text("hello", encoding="utf-8")

    assert expiry.certificate_file(str(tmp_path / "x.pem")).reason == "not a PEM certificate"


def serve(pem: Path, private: Path) -> tuple[int, threading.Thread, list[object]]:
    import socket

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(pem, private)
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    server.settimeout(5)
    handled: list[object] = []

    def run() -> None:
        for _ in range(2):
            try:
                connection, _ = server.accept()
                with context.wrap_socket(connection, server_side=True):
                    handled.append(1)
            except (OSError, ssl.SSLError):
                handled.append(0)

        server.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return server.getsockname()[1], thread, handled


def test_a_host_says_when_its_certificate_ends_and_that_it_would_not_be_trusted(tmp_path: Path) -> None:
    ends = datetime(2027, 1, 23, 19, 10, 54, tzinfo=timezone.utc)
    pem, private = make_certificate(tmp_path, ends)
    port, thread, _ = serve(pem, private)
    found = expiry.certificate_host(f"localhost:{port}")
    thread.join(10)

    assert found.ends == ends
    assert found.problem and "self-signed" in found.problem or "unable to get" in found.problem


def test_a_host_that_does_not_answer_is_not_read() -> None:
    found = expiry.certificate_host("localhost:1", timeout=1)

    assert found.ends is None and found.reason


RDAP = json.dumps(
    {
        "events": [
            {"eventAction": "registration", "eventDate": "2026-03-11T08:21:40.651446Z"},
            {"eventAction": "expiration", "eventDate": "2029-03-11T08:21:40.63405Z"},
            {"eventAction": "last changed", "eventDate": "2026-03-16T08:22:20.721667Z"},
        ],
        "status": ["client transfer prohibited"],
    }
)


@pytest.fixture(autouse=True)
def forget_answers() -> None:
    expiry._ANSWERS.clear()


def test_the_expiry_of_a_domain_is_the_expiration_event_of_the_registry() -> None:
    assert expiry.parse_rdap(RDAP) == datetime(2029, 3, 11, 8, 21, 40, tzinfo=timezone.utc)
    assert expiry.parse_rdap('{"errorCode": 404}') is None
    assert expiry.parse_rdap("not json") is None
    assert expiry.parse_rdap('{"events": "x"}') is None


def test_a_registry_that_publishes_nothing_is_not_read_unless_the_owner_gave_the_date() -> None:
    nothing = lambda url: '{"errorCode": 404}'  # noqa: E731

    assert expiry.domain_expiry("example.eu", fetch=nothing).ends is None
    assert "does not publish" in expiry.domain_expiry("example.eu", fetch=nothing).reason

    expiry._ANSWERS.clear()

    assert expiry.domain_expiry("example.eu", "2027-03-01", fetch=nothing).ends == datetime(2027, 3, 1, 23, 59, tzinfo=timezone.utc)


def test_a_registry_that_does_not_answer_says_why_and_is_asked_again_later() -> None:
    def refused(url: str) -> str:
        raise urllib.error.HTTPError(url, 404, "no", None, None)  # type: ignore[arg-type]

    def down(url: str) -> str:
        raise OSError("timed out")

    assert expiry.domain_expiry("a.example", fetch=refused).reason == "the registry does not answer for this domain (HTTP 404)"
    assert "timed out" in expiry.domain_expiry("b.example", fetch=down).reason


def test_a_domain_is_asked_of_its_registry_once_not_at_every_pass() -> None:
    asked: list[str] = []

    def fetch(url: str) -> str:
        asked.append(url)

        return RDAP

    first = expiry.domain_expiry("example.org", fetch=fetch)
    second = expiry.domain_expiry("example.org", fetch=fetch)

    assert first == second and asked == ["https://rdap.org/domain/example.org"]


def test_each_declared_thing_is_read_on_its_own() -> None:
    reading = expiry.read_expiries(
        ("/etc/x.pem", "host.example"),
        {"b.example": "", "a.example": "2027-01-01"},
        host=lambda entry: Expiry(entry, NOW),
        file=lambda entry: Expiry(entry, None, "denied"),
        domain=lambda name, declared: Expiry(name, None, declared or "none"),
    )

    assert [item.name for item in reading.certificates] == ["/etc/x.pem", "host.example"] and reading.certificates[0].reason == "denied"
    assert [item.name for item in reading.domains] == ["a.example", "b.example"]


# The controls.
def ends_in(days: float, name: str = "home.example", **changes: str) -> Expiry:
    return Expiry(name, NOW + timedelta(days=days), **changes)


def judged(certificates: tuple[Expiry, ...] | None = None, domains: tuple[Expiry, ...] | None = None, definition: BootChecksDefinition | None = None) -> dict[str, Result]:
    wide = definition or BootChecksDefinition(certificates=("home.example",), domains={"example.org": ""})
    reading = ExpiryReading(certificates or (), domains or ()) if certificates is not None or domains is not None else None

    return {result.control: result for result in evaluate(facts(), wide, NOW, expiry=reading)}


def test_nothing_declared_is_skipped_and_asks_nothing() -> None:
    found = judged(None, None, BootChecksDefinition())

    assert found["certificates"].status == SKIPPED and found["certificates"].summary == "no certificate declared"
    assert found["domains"].summary == "no domain declared"


def test_declared_but_not_read_is_skipped_and_says_so() -> None:
    assert judged()["certificates"].summary == "certificates were not read"


def test_the_wildcard_certificate_of_the_26_november_is_valid_for_57_days() -> None:
    found = judged((Expiry("/srv/npm/fullchain.pem", datetime(2027, 1, 23, 19, 10, 54, tzinfo=timezone.utc)),), ())["certificates"]

    assert found.status == OK and found.summary == "1 certificate(s) valid, the nearest ends in 57 day(s)"


def test_a_certificate_ending_soon_is_to_watch_and_within_a_week_is_to_fix() -> None:
    soon = judged((ends_in(15.5), ends_in(90, "other.example")), ())["certificates"]
    urgent = judged((ends_in(5.2), ends_in(15.5, "other.example")), ())["certificates"]

    assert soon.status == "warning" and soon.finding == "certificate_soon" and soon.summary == "1 certificate(s) to renew"
    assert soon.details[0] == "home.example: ends in 15 day(s) (2026-12-12)"
    assert urgent.status == "critical" and urgent.finding == "certificate_urgent"
    assert [line.split(":")[0] for line in urgent.details[:2]] == ["home.example", "other.example"]
    assert urgent.details[-1].startswith("to do: renew the certificates above")


def test_a_certificate_past_its_date_is_to_fix_and_says_since_when() -> None:
    found = judged((ends_in(-2.5),), ())["certificates"]

    assert found.status == "critical" and found.details[0] == "home.example: ended 3 day(s) ago (2026-11-24)"


def test_a_certificate_that_would_not_be_trusted_is_to_watch_even_when_it_is_far_from_its_end() -> None:
    found = judged((ends_in(80, problem="self-signed certificate"),), ())["certificates"]

    assert found.status == "warning" and found.finding == "certificate_invalid"
    assert found.summary == "1 certificate(s) not trusted" and found.details[0] == "home.example: not trusted: self-signed certificate"


def test_a_certificate_that_could_not_be_read_is_unknown_never_fine() -> None:
    found = judged((Expiry("home.example", None, "timed out"),), ())["certificates"]

    assert found.status == UNKNOWN and found.summary == "1 declared certificate(s) not read" and found.details == ("home.example: not read: timed out",)


def test_a_late_certificate_outweighs_one_not_read_and_the_other_is_still_told() -> None:
    found = judged((ends_in(3), Expiry("b.example", None, "refused")), ())["certificates"]

    assert found.status == "critical" and "b.example: not read: refused" in found.details


def test_the_domains_have_their_own_limits() -> None:
    far = judged((), (ends_in(900, "example.org"),))["domains"]
    soon = judged((), (ends_in(50, "example.org"),))["domains"]
    urgent = judged((), (ends_in(10, "example.org"),))["domains"]

    assert far.status == OK and far.summary == "1 domain(s) valid, the nearest ends in 900 day(s)"
    assert soon.status == "warning" and soon.finding == "domain_soon" and soon.details[-1].startswith("to do: renew the domains above")
    assert urgent.status == "critical" and urgent.finding == "domain_urgent"


def test_what_the_owner_ignores_or_moves_is_judged_as_declared() -> None:
    quiet = BootChecksDefinition(certificates=("home.example",), severity={"certificate_soon": "ignore"})
    moved = BootChecksDefinition(certificates=("home.example",), certificate_days=60)

    assert judged((ends_in(15),), (), quiet)["certificates"].status == SKIPPED
    assert judged((ends_in(45),), (), moved)["certificates"].status == "warning"
    assert judged((ends_in(45),), ())["certificates"].status == OK


def test_the_expiry_is_told_in_french() -> None:
    fr = translator_for("fr")
    found = judged((ends_in(15.5),), ())["certificates"]

    assert say(fr, found.summary) == "1 certificat(s) à renouveler"
    assert say(fr, found.details[0]) == "home.example : se termine dans 15 jour(s) (2026-12-12)"
    assert say(fr, "home.example: not read: timed out") == "home.example : non lu : timed out"


# The declaration.
def load(tmp_path: Path, text: str) -> BootChecksDefinition:
    path = tmp_path / "b.yml"
    path.write_text(text, encoding="utf-8")

    return load_boot_checks_yaml(path)


def test_the_declaration_names_certificates_and_domains_and_a_date_for_a_registry_that_has_none(tmp_path: Path) -> None:
    definition = load(tmp_path, "certificates: [www.example.org, 'www.example.org:8443', /srv/proxy/fullchain.pem, www.example.org]\ndomains:\n  example.org:\n  example.eu: 2027-03-01\ncertificate_days: 30\n")

    assert definition.certificates == ("www.example.org", "www.example.org:8443", "/srv/proxy/fullchain.pem")
    assert definition.domains == {"example.org": "", "example.eu": "2027-03-01"}
    assert definition.certificate_days == 30 and definition.domain_days == 60
    assert load(tmp_path, "domains: [a.example, b.example]\n").domains == {"a.example": "", "b.example": ""}


@pytest.mark.parametrize(
    "text",
    ["certificates: x\n", "certificates: ['a b']\n", "certificates: ['/etc/../x.pem']\n", "certificates: [relative/x.pem]\n", "domains: ['nodot']\n", "domains: {a.example: soon}\n", "domains: x\n"],
)
def test_what_is_neither_a_host_nor_a_path_nor_a_domain_is_refused(tmp_path: Path, text: str) -> None:
    with pytest.raises(ValueError, match=r"certificates|domains"):
        load(tmp_path, text)


def test_the_shipped_declaration_asks_nothing_on_the_network() -> None:
    shipped = Path(__file__).resolve().parents[3] / "src/aistack/boot_checks/definitions/boot_checks.yml"
    definition = load_boot_checks_yaml(shipped)

    assert definition.certificates == () and definition.domains == {} and dt.date.today().year >= 2026
