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
    applies_to: ["any"]
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
                    {"Names": name, "State": "running"}
                    for name in self._logs
                ]
            }
        }

    def collect_logs(self, subject: str, depth: int, state: str):
        lines = self._logs[subject]

        if isinstance(lines, Exception):
            raise lines

        last = len(lines) - 1

        return RuntimeObservation(
            subject=subject,
            provider="fake",
            state=state,
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
    assert "AUTH_FAILED" in out


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
    assert "[sonarr · running]" in out
    assert "gluetun" not in out


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


def test_a_line_that_fits_is_printed_whole_and_unmarked(
    monkeypatch, catalogue_file, capsys
):

    line = "AUTH_FAILED " + "x" * 100

    run(monkeypatch, catalogue_file, {"gluetun": [line]})
    out = capsys.readouterr().out

    assert line in out
    assert "char cut]" not in out


def test_a_cut_evidence_line_says_how_much_it_hid(
    monkeypatch, catalogue_file, capsys
):
    """
    The heritage refuses to trim the number of evidence lines in
    silence; the same rule applies inside a line. What is cut is
    counted on the side it was cut from, because a bare ellipsis
    would misplace the match in the reader's head.
    """

    line = "AUTH_FAILED " + "x" * 300

    run(monkeypatch, catalogue_file, {"gluetun": [line]})
    out = capsys.readouterr().out

    assert "cut]" in out
    assert "AUTH_FAILED" in out


def test_a_match_at_the_end_of_a_long_line_is_still_shown(
    monkeypatch, tmp_path, capsys
):
    """
    The reason this changed on 2026-08-23. An extract taken from
    the start shows the pattern only when the pattern is near the
    start — which is a property of the log, not of the rule. A
    centred window shows it wherever it sits.

    Here the pattern is 600 characters in, three times the width.
    A prefix extract would show three hundred `x` and nothing
    else, and the report would state that a rule fired without
    ever showing what fired it.
    """

    catalogue = tmp_path / "OPS-TEST.md"
    catalogue.write_text(CATALOGUE, encoding="utf-8")

    line = "x" * 600 + " AUTH_FAILED " + "y" * 600

    run(monkeypatch, catalogue, {"gluetun": [line]})
    out = capsys.readouterr().out

    assert "AUTH_FAILED" in out
    assert "cut]" in out


def test_the_extract_is_centred_rather_than_ending_at_the_match(
    monkeypatch, tmp_path, capsys
):
    """
    Context on both sides. A window that ended at the match would
    show what fired the rule and nothing of what surrounded it,
    and the surrounding text is what a human reads to decide
    whether the finding matters.
    """

    catalogue = tmp_path / "OPS-TEST.md"
    catalogue.write_text(CATALOGUE, encoding="utf-8")

    line = "a" * 600 + "AUTH_FAILED" + "b" * 600

    run(monkeypatch, catalogue, {"gluetun": [line]})
    out = capsys.readouterr().out

    assert "aaaAUTH_FAILEDbbb" in out


def test_the_real_nginx_line_shows_the_pattern_that_fired(
    monkeypatch, tmp_path, capsys
):
    """
    The line that exposed the defect, verbatim from `frigate` on
    2026-08-21, with the pattern where it actually sat.
    """

    catalogue = tmp_path / "OPS-TEST.md"
    catalogue.write_text(
        CATALOGUE.replace('"AUTH_FAILED"', '"connection refused"')
        .replace("case_sensitive: true", "case_sensitive: false"),
        encoding="utf-8",
    )

    line = (
        "2026-08-21 17:20:10.948256087  2026/08/21 17:20:10 [error] "
        "267#267: *1 connect() failed (111: Connection refused) while "
        "connecting to upstream, client: 172.18.0.1, server: , "
        'request: "GET / HTTP/1.1", upstream: "http://127.0.0.1:5000/"'
    )

    run(monkeypatch, catalogue, {"frigate": [line]})
    out = capsys.readouterr().out

    assert "Connection refused" in out


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


# --------------------------------------------------------------------
# Grounding a finding against the lifecycle register, STD-0300 4.7
# --------------------------------------------------------------------


LIFECYCLE = """# A register

```lifecycle
artifact: OPS-TEST-LC
declarations:
  - container: frigate
    expected: intermittent
    reason: "Stopped most of the time to save resources."
```
"""


def test_a_finding_about_a_declared_container_is_grounded(
    monkeypatch, catalogue_file, tmp_path, capsys
):
    register = tmp_path / "OPS-TEST-LC.md"
    register.write_text(LIFECYCLE, encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_LIFECYCLE_REGISTER", register)

    run(monkeypatch, catalogue_file, {"frigate": ["AUTH_FAILED"]})
    out = capsys.readouterr().out

    assert "grounding: OPS-TEST-LC/frigate" in out
    assert "Stopped most of the time to save resources" in out


def test_a_finding_about_an_undeclared_container_stays_unknown(
    monkeypatch, catalogue_file, tmp_path, capsys
):
    register = tmp_path / "OPS-TEST-LC.md"
    register.write_text(LIFECYCLE, encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_LIFECYCLE_REGISTER", register)

    run(monkeypatch, catalogue_file, {"gluetun": ["AUTH_FAILED"]})
    out = capsys.readouterr().out

    assert "grounding: unknown" in out


def test_a_missing_lifecycle_register_still_diagnoses_and_says_so(
    monkeypatch, catalogue_file, tmp_path, capsys
):
    monkeypatch.setattr(
        cli, "DEFAULT_LIFECYCLE_REGISTER", tmp_path / "absent.md"
    )

    code = run(monkeypatch, catalogue_file, {"gluetun": ["AUTH_FAILED"]})
    out = capsys.readouterr().out

    assert code == 1
    assert "no lifecycle register at" in out
    assert "grounding: unknown" in out


def test_an_unreadable_lifecycle_register_still_diagnoses_and_says_why(
    monkeypatch, catalogue_file, tmp_path, capsys
):
    register = tmp_path / "broken.md"
    register.write_text("# no block here\n", encoding="utf-8")
    monkeypatch.setattr(cli, "DEFAULT_LIFECYCLE_REGISTER", register)

    code = run(monkeypatch, catalogue_file, {"gluetun": ["AUTH_FAILED"]})
    out = capsys.readouterr().out

    assert code == 1
    assert "lifecycle register not readable" in out


def test_the_governed_lifecycle_register_is_the_default():
    """
    Mirrors `test_the_governed_catalogue_is_the_default`: the
    default path resolves to the governed artifact, and fails
    loudly rather than silently if the layout moves.
    """

    assert cli.DEFAULT_LIFECYCLE_REGISTER.exists()
    assert cli.DEFAULT_LIFECYCLE_REGISTER.name == (
        "OPS-0003-Container-Lifecycle-Declarations.md"
    )
