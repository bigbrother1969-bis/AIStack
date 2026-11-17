from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.declaration import observe, write_declaration
from aistack.kernel.bootstrap.default import create_kernel


@pytest.fixture
def host(tmp_path: Path):
    config = tmp_path / "config"
    generated = tmp_path / "data"
    shipped = tmp_path / "package" / "hosts.yml"
    config.mkdir()
    shipped.parent.mkdir()
    shipped.write_text("shipped\n", encoding="utf-8")
    return config, generated, [shipped]


def _transactions():
    return create_kernel().services.transactions


def _pass(host):
    config, generated, shipped = host
    changes = observe.observe(config, generated, shipped)
    records, problems = observe.apply(_transactions(), config, generated, changes)
    return changes, records, problems


def test_the_first_sight_is_a_reference_and_records_nothing(host) -> None:
    config, generated, _ = host
    (config / "hosts.yml").write_text("a: 1\n", encoding="utf-8")

    changes, records, problems = _pass(host)

    assert [(item.name, item.kind) for item in changes] == [("hosts.yml", observe.REFERENCE)]
    assert records == [] and problems == []
    assert observe.seen_path(generated, "hosts.yml").read_text(encoding="utf-8") == "a: 1\n"
    assert not (generated / observe.RECORD).exists()
    assert not (generated / "declaration-change.json").exists()


def test_an_unchanged_file_is_not_seen_again(host) -> None:
    config, _, _ = host
    (config / "hosts.yml").write_text("a: 1\n", encoding="utf-8")
    _pass(host)

    changes, records, _ = _pass(host)

    assert changes == [] and records == []


def test_a_hand_edit_is_recorded_with_the_previous_content_kept(host) -> None:
    config, generated, _ = host
    (config / "hosts.yml").write_text("a: 1\n", encoding="utf-8")
    _pass(host)
    (config / "hosts.yml").write_text("a: 2\n# secret-looking comment\n", encoding="utf-8")

    changes, records, problems = _pass(host)

    assert [(item.name, item.kind) for item in changes] == [("hosts.yml", observe.EDITED)]
    assert problems == [] and len(records) == 1
    record = json.loads((generated / observe.RECORD).read_text(encoding="utf-8"))
    assert record["name"] == "hosts.yml" and record["author"] == observe.AUTHOR
    assert record["before"] != record["after"]
    assert "secret-looking" not in json.dumps(record)
    assert Path(record["copy"]).read_text(encoding="utf-8") == "a: 1\n"
    assert observe.seen_path(generated, "hosts.yml").read_text(encoding="utf-8") == "a: 2\n# secret-looking comment\n"
    assert list((generated / "history" / "declaration-observed").glob("*.json"))
    assert not (generated / "declaration-change.json").exists()
    assert _pass(host)[0] == []


def test_a_file_a_screen_wrote_is_followed_and_recorded_once(host) -> None:
    config, generated, _ = host
    path = config / "hosts.yml"
    path.write_text("a: 1\n", encoding="utf-8")
    _pass(host)

    write_declaration(_transactions(), generated, path, "a: 3\n", "Fabrice", "from a screen")
    changes, records, _ = _pass(host)

    assert [(item.name, item.kind) for item in changes] == [("hosts.yml", observe.FOLLOW)]
    assert records == [] and not (generated / observe.RECORD).exists()
    assert observe.seen_path(generated, "hosts.yml").read_text(encoding="utf-8") == "a: 3\n"

    path.write_text("a: 4\n", encoding="utf-8")
    again, records, _ = _pass(host)

    assert [(item.name, item.kind) for item in again] == [("hosts.yml", observe.EDITED)]
    assert len(records) == 1


def test_a_file_edited_back_to_what_a_screen_wrote_is_not_an_edit(host) -> None:
    config, generated, _ = host
    path = config / "hosts.yml"
    path.write_text("a: 1\n", encoding="utf-8")
    _pass(host)
    write_declaration(_transactions(), generated, path, "a: 3\n", "Fabrice", "screen")
    _pass(host)
    path.write_text("a: 9\n", encoding="utf-8")
    _pass(host)

    path.write_text("a: 3\n", encoding="utf-8")
    changes, _, _ = _pass(host)

    assert [(item.name, item.kind) for item in changes] == [("hosts.yml", observe.FOLLOW)]


def test_a_file_the_package_does_not_ship_is_left_alone(host) -> None:
    config, generated, _ = host
    (config / "volumes.yml").write_text("x: 1\n", encoding="utf-8")

    changes, _, _ = _pass(host)

    assert changes == []
    assert not (generated / observe.SEEN).exists()


def test_a_file_that_changed_again_since_it_was_observed_waits_for_the_next_pass(host) -> None:
    config, generated, shipped = host
    path = config / "hosts.yml"
    path.write_text("a: 1\n", encoding="utf-8")
    _pass(host)
    path.write_text("a: 2\n", encoding="utf-8")
    changes = observe.observe(config, generated, shipped)
    path.write_text("a: 3\n", encoding="utf-8")

    records, problems = observe.apply(_transactions(), config, generated, changes)

    assert records == [] and problems == []
    assert observe.seen_path(generated, "hosts.yml").read_text(encoding="utf-8") == "a: 1\n"
    assert [item.kind for item in observe.observe(config, generated, shipped)] == [observe.EDITED]


def test_a_file_that_is_not_utf8_is_a_problem_and_is_left_as_it_is(host) -> None:
    config, generated, _ = host
    (config / "hosts.yml").write_bytes(b"caf\xe9: 1\n")

    changes, records, problems = _pass(host)

    assert [item.kind for item in changes] == [observe.REFERENCE]
    assert records == [] and problems == ["hosts.yml: not UTF-8, not observed"]
    assert not observe.seen_path(generated, "hosts.yml").exists()


def test_crlf_line_ends_are_kept_byte_for_byte(host) -> None:
    config, generated, _ = host
    (config / "hosts.yml").write_bytes(b"a: 1\r\nb: 2\r\n")

    _pass(host)

    assert observe.seen_path(generated, "hosts.yml").read_bytes() == b"a: 1\r\nb: 2\r\n"
    assert _pass(host)[0] == []
