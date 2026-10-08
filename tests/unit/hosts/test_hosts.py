from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.cli import hosts as hosts_cli
from aistack.hosts.records import HostsDeclaration, TracedHost, load_hosts_declaration, read_host
from aistack.timemachine.iri import host_event_iri, stream_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_host_changes
from aistack.timemachine.projection.host_changes import describe_event
from aistack.timemachine.screen import ribbon_group
from aistack.timemachine.vocabulary import (
    AISTACK_HOST_ACTION,
    AISTACK_HOST_DETAIL,
    AISTACK_HOST_EVENT_KIND,
    AISTACK_STABLE_SUBJECT,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_GENERATED_BY,
)

NOW = datetime(2026, 10, 8, 19, 0, tzinfo=timezone.utc)
EVENTS = [
    {"at": "2026-03-01T10:00:00+00:00", "host": "raspberry", "kind": "package", "action": "install",
     "package": "foo:arm64", "from": None, "to": "1.0"},
    {"at": "2026-10-08T06:50:58+00:00", "host": "raspberry", "kind": "apt", "commandline": "apt-get -y upgrade",
     "requested_by": "pi (1000)", "counts": {"upgrade": 2}, "ended": None},
    {"at": "2026-10-08T18:49:13+00:00", "host": "raspberry", "kind": "baseline", "files": 1664, "units": 261},
    {"at": "2026-10-08T19:04:13+00:00", "host": "raspberry", "kind": "file", "action": "modified",
     "path": "/etc/ssh/sshd_config",
     "before": {"size": 8, "mode": "0o644", "owner": "0:0", "fp": "aa"},
     "after": {"size": 10, "mode": "0o644", "owner": "0:0", "fp": "bb"}},
    {"at": "2026-10-08T19:04:13+00:00", "host": "raspberry", "kind": "unit", "unit": "watchtower.timer",
     "before": "enabled", "after": "disabled"},
]


def _host(tmp_path: Path, *, last_run: str = "2026-10-08T18:49:13+00:00") -> TracedHost:
    directory = tmp_path / "raspberry"
    directory.mkdir()
    (directory / "host.json").write_text(json.dumps({"last_run": last_run, "seconds": 10.6, "files": 1664,
                                                       "units": 261, "problems": []}))
    (directory / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in EVENTS) + "not json\n")
    return TracedHost("raspberry", directory)


def test_the_shipped_declaration_traces_both_hosts(tmp_path: Path):
    declaration = load_hosts_declaration(tmp_path)

    assert [h.name for h in declaration.hosts] == ["gigabyte", "raspberry"]
    assert declaration.hosts[0].directory == tmp_path / "hosts" / "gigabyte"
    assert declaration.hosts[1].directory == Path("/media/BACKUP/AIStack/hosts/raspberry")
    assert declaration.silent_after == timedelta(minutes=60)


def test_records_are_read_line_by_line_and_a_bad_line_skipped(tmp_path: Path):
    records = read_host(_host(tmp_path))

    assert [number for number, _ in records.events] == [1, 2, 3, 4, 5]
    assert not records.problem and records.last_run == datetime(2026, 10, 8, 18, 49, 13, tzinfo=timezone.utc)


def test_a_host_whose_disk_is_not_mounted_is_said(tmp_path: Path):
    records = read_host(TracedHost("raspberry", tmp_path / "absent"))

    assert "not mounted" in records.problem and records.events == []


def test_a_collector_that_stopped_running_is_silent(tmp_path: Path):
    records = read_host(_host(tmp_path))

    assert not records.silent(NOW, timedelta(minutes=60))
    assert records.silent(NOW + timedelta(hours=2), timedelta(minutes=60))


def test_what_the_graph_keeps_of_each_event_never_a_fingerprint():
    described = [describe_event("raspberry", event) for event in EVENTS]

    assert described == [
        ("raspberry/package/foo", "install", "∅ → 1.0"),
        ("raspberry/apt", "run", "apt-get -y upgrade (upgrade 2)"),
        ("raspberry", "baseline", "1664 files, 261 units"),
        ("raspberry:/etc/ssh/sshd_config", "modified", "size, content"),
        ("raspberry/unit/watchtower.timer", "disabled", "enabled → disabled"),
    ]
    assert not any("aa" in detail or "bb" in detail for _, _, detail in described)


def test_each_event_is_an_entity_of_its_host_s_stream(tmp_path: Path):
    graph = OxigraphGraphStore(tmp_path / "graph")
    unreadable = read_host(TracedHost("gigabyte", tmp_path / "absent"))

    summary = project_host_changes(graph, [read_host(_host(tmp_path)), unreadable])

    assert (summary.hosts_seen, summary.hosts_unreadable, summary.events_seen) == (2, 1, 5)
    entity = host_event_iri("raspberry", 4)

    def values(predicate: str) -> set:
        return {row["o"] for row in graph.query(f"SELECT ?o WHERE {{ <{entity}> <{predicate}> ?o }}")}

    assert values(PROV_WAS_GENERATED_BY) == {stream_iri("host-raspberry")}
    assert values(PROV_GENERATED_AT_TIME) and values(AISTACK_STABLE_SUBJECT) == {"raspberry:/etc/ssh/sshd_config"}
    assert values(AISTACK_HOST_EVENT_KIND) == {"file"} and values(AISTACK_HOST_ACTION) == {"modified"}
    assert values(AISTACK_HOST_DETAIL) == {"size, content"}


def test_the_hosts_have_their_own_group_on_the_ribbon():
    assert ribbon_group("host-raspberry") == "hosts"
    assert ribbon_group("docker-digest") == "docker"
    assert ribbon_group("dock") == "observation"


def test_the_command_says_each_host_and_fails_on_a_silent_one(tmp_path: Path, capsys, monkeypatch):
    host = _host(tmp_path)
    monkeypatch.setattr(hosts_cli, "load_hosts_declaration",
                        lambda generated_dir: HostsDeclaration((host,), timedelta(minutes=60)))

    assert hosts_cli.main(["--last", "2"], root=tmp_path, now=NOW) == 0
    shown = capsys.readouterr().out
    assert "baseline 1" in shown and "watchtower.timer" in shown

    assert hosts_cli.main([], root=tmp_path, now=NOW + timedelta(hours=3)) == 1
    assert "SILENCIEUX" in capsys.readouterr().out
