from datetime import datetime, timezone
from pathlib import Path

import pytest

from aistack.cli import runtime_diagnose as cli
from aistack.contracts.runtime_observation import (
    LogEntry,
    RuntimeObservation,
)


NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


CATALOGUE = """# A catalogue

```signatures
artifact: OPS-TEST
signatures:
  - identifier: OPS-TEST/S-001
    pattern: "AUTH_FAILED"
    case_sensitive: true
    interpretation: "OpenVPN reports an AUTH_FAILED error."
    remediation: "Check the VPN credentials the container uses."
    depth: 10
    confidence: Declared
    grounding: unknown
```
"""


@pytest.fixture
def catalogue_file(tmp_path: Path) -> Path:
    path = tmp_path / "OPS-TEST.md"
    path.write_text(CATALOGUE, encoding="utf-8")
    return path


class FakeProvider:
    """
    A provider that observes without a Docker daemon.

    The chain under test is catalogue → subjects → observation →
    qualification → exit code. Docker itself is exercised
    nowhere: `collect_logs` is covered by its own tests, and a
    daemon would make these results depend on this machine.
    """

    def __init__(self, logs: dict[str, list[str] | Exception]):
        self._logs = logs

    def collect(self):
        return {
            "docker": {
                "containers": [
                    {"Names": name} for name in self._logs
                ]
            }
        }

    def collect_logs(self, subject: str, depth: int):
        lines = self._logs[subject]

        if isinstance(lines, Exception):
            raise lines

        last = len(lines) - 1

        return RuntimeObservation(
            subject=subject,
            provider="fake",
            collected_at=NOW,
            depth=depth,
            entries=tuple(
                LogEntry(offset=last - i, text=t)
                for i, t in enumerate(lines)
            ),
        )


def run(monkeypatch, catalogue_file, logs, argv=()) -> int:
    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeProvider(logs))
    monkeypatch.setattr(
        "sys.argv",
        ["runtime_diagnose", "--catalogue", str(catalogue_file), *argv],
    )

    try:
        cli.main()
    except SystemExit as exit:
        return exit.code or 0

    # A run with nothing to report returns rather than raising,
    # as `knowledge_integrity` does. The shell sees 0 either way.
    return 0


# --------------------------------------------------------------------


def test_a_quiet_host_exits_zero(monkeypatch, catalogue_file, capsys):

    code = run(monkeypatch, catalogue_file, {"gluetun": ["all quiet"]})

    assert code == 0
    assert "No finding." in capsys.readouterr().out


def test_a_finding_exits_one_and_cites_its_signature(
    monkeypatch, catalogue_file, capsys
):

    code = run(
        monkeypatch, catalogue_file, {"gluetun": ["AUTH_FAILED"]}
    )
    out = capsys.readouterr().out

    assert code == 1
    assert "OPS-TEST/S-001" in out
    assert "Check the VPN credentials" in out
    assert "-0: AUTH_FAILED" in out


def test_every_container_is_examined_when_none_is_named(
    monkeypatch, catalogue_file, capsys
):
    """
    STD-0300 § VS-4 criterion 4.1: detection without being
    pointed at a service. The experimenter required a container
    name; this does not.
    """

    run(
        monkeypatch,
        catalogue_file,
        {"gluetun": ["AUTH_FAILED"], "sonarr": ["quiet"], "radarr": ["quiet"]},
    )

    assert "Subjects examined: 3" in capsys.readouterr().out


def test_naming_a_container_examines_only_that_one(
    monkeypatch, catalogue_file, capsys
):

    run(
        monkeypatch,
        catalogue_file,
        {"gluetun": ["AUTH_FAILED"], "sonarr": ["AUTH_FAILED"]},
        argv=("sonarr",),
    )
    out = capsys.readouterr().out

    assert "Subjects examined: 1" in out
    assert "[sonarr]" in out
    assert "[gluetun]" not in out


def test_a_subject_that_cannot_be_read_makes_the_sweep_partial(
    monkeypatch, catalogue_file, capsys
):
    """
    A partial sweep reporting "no finding" would be read as
    "nothing is wrong". Exit 2 says the run did not do what it
    was asked, and it outranks the findings.
    """

    code = run(
        monkeypatch,
        catalogue_file,
        {
            "gluetun": ["AUTH_FAILED"],
            "gone": OSError("No such container: gone"),
        },
    )
    out = capsys.readouterr().out

    assert code == 2
    assert "Not observed:" in out
    assert "gone" in out
    assert "unobserved: 1" in out


def test_a_missing_catalogue_exits_two(monkeypatch, tmp_path, capsys):

    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeProvider({}))
    monkeypatch.setattr(
        "sys.argv",
        ["runtime_diagnose", "--catalogue", str(tmp_path / "absent.md")],
    )

    with pytest.raises(SystemExit) as exit:
        cli.main()

    assert exit.value.code == 2
    assert "pass --catalogue" in capsys.readouterr().out


def test_an_unreadable_catalogue_exits_two_and_says_why(
    monkeypatch, tmp_path, capsys
):

    broken = tmp_path / "broken.md"
    broken.write_text("# no block here\n", encoding="utf-8")

    monkeypatch.setattr(cli, "DockerProvider", lambda: FakeProvider({}))
    monkeypatch.setattr(
        "sys.argv", ["runtime_diagnose", "--catalogue", str(broken)]
    )

    with pytest.raises(SystemExit) as exit:
        cli.main()

    assert exit.value.code == 2
    assert "no ```signatures block" in capsys.readouterr().out


def test_evidence_beyond_three_lines_is_counted_not_hidden(
    monkeypatch, catalogue_file, capsys
):
    """
    The report shows three lines and says how many more the
    finding carries. A trimmed report that did not say so would
    read as complete.
    """

    run(monkeypatch, catalogue_file, {"gluetun": ["AUTH_FAILED"] * 7})
    out = capsys.readouterr().out

    assert "evidence: 7 line(s)" in out
    assert "4 further line(s) not shown" in out


def test_the_window_read_is_the_deepest_the_catalogue_declares(
    monkeypatch, catalogue_file, capsys
):

    run(monkeypatch, catalogue_file, {"gluetun": ["quiet"]})

    assert "Window: 10 lines" in capsys.readouterr().out


def test_the_governed_catalogue_is_the_default(monkeypatch):
    """
    The default path resolves to the governed artifact, from this
    module's location. If the layout moves, this fails rather
    than silently diagnosing against nothing.
    """

    assert cli.DEFAULT_CATALOGUE.exists()
    assert cli.DEFAULT_CATALOGUE.name == (
        "OPS-0001-Container-Log-Signatures.md"
    )
