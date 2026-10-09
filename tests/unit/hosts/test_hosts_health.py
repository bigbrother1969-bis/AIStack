"""The Hosts domain of the health cockpit (2.0, 2026-10-09)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aistack.hosts.health import DOMAIN, find_silent_hosts, hosts_domain
from aistack.hosts.records import HostRecords
from aistack.i18n import translator_for

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _host(root: Path, name: str, last_run: str | None) -> Path:
    directory = root / "hosts" / name
    directory.mkdir(parents=True)
    if last_run is not None:
        (directory / "host.json").write_text(json.dumps({"last_run": last_run}), encoding="utf-8")
    return directory


def _declaration(root: Path, *names: str, extra: str = "") -> Path:
    path = root / "hosts.yml"
    body = "silent_after_minutes: 60\nhosts:\n" + "".join(
        f"  {name}:\n    directory: hosts/{name}\n" for name in names
    )
    path.write_text(body + extra, encoding="utf-8")
    return path


def test_a_host_written_recently_is_not_a_finding(tmp_path: Path) -> None:
    _host(tmp_path, "gigabyte", "2026-10-09T11:50:00+00:00")
    domain = hosts_domain(tmp_path, NOW, _declaration(tmp_path, "gigabyte"))
    assert domain.name == DOMAIN and domain.instrumented and domain.findings == ()


def test_a_host_silent_longer_than_declared_is_a_finding(tmp_path: Path) -> None:
    _host(tmp_path, "gigabyte", "2026-10-09T11:50:00+00:00")
    _host(tmp_path, "raspberry", "2026-10-09T09:30:00+00:00")
    domain = hosts_domain(tmp_path, NOW, _declaration(tmp_path, "gigabyte", "raspberry"))

    (finding,) = domain.findings
    assert finding.subject == "raspberry"
    assert "150 minutes" in finding.interpretation
    assert finding.qualifications == ("OPS-0004/deployment-misconfiguration",)


def test_a_host_with_no_record_is_a_finding_that_says_why(tmp_path: Path) -> None:
    _host(tmp_path, "gigabyte", "2026-10-09T11:50:00+00:00")
    domain = hosts_domain(
        tmp_path,
        NOW,
        _declaration(tmp_path, "gigabyte", extra=f"  raspberry:\n    directory: {tmp_path}/unmounted\n"),
    )

    (finding,) = domain.findings
    assert finding.subject == "raspberry"
    assert "not mounted" in finding.interpretation


def test_an_unreadable_declaration_is_not_instrumented(tmp_path: Path) -> None:
    domain = hosts_domain(tmp_path, NOW, tmp_path / "missing.yml")
    assert not domain.instrumented and "not readable" in domain.note


def test_the_english_catalog_says_exactly_what_the_finding_says(tmp_path: Path) -> None:
    _host(tmp_path, "raspberry", "2026-10-09T09:30:00+00:00")
    domain = hosts_domain(
        tmp_path,
        NOW,
        _declaration(tmp_path, "raspberry", extra=f"  pi2:\n    directory: {tmp_path}/none\n"),
    )
    t = translator_for("en")
    for finding in domain.findings:
        assert finding.message is not None
        said = " ".join(t(p.key, **dict(p.params)) for p in finding.message.interpretation)
        assert said == finding.interpretation
        done = " ".join(t(p.key, **dict(p.params)) for p in finding.message.remediation)
        assert done == finding.remediation


def test_a_naive_last_run_is_read_in_the_clock_zone() -> None:
    records = HostRecords("gigabyte", Path("/x"), summary={"last_run": "2026-10-09T11:59:00"})
    assert find_silent_hosts([records], NOW, 60) == ()
