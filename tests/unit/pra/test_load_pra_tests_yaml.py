from datetime import datetime, timezone
from pathlib import Path

import pytest

from aistack.pra.yaml import load_pra_tests_yaml


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_complete_definition_is_loaded(tmp_path: Path):
    path = write(
        tmp_path / "pra_tests.yml",
        """
        max_age_days: 90

        services:
          - name: gigabyte
            last_test: null
          - name: nextcloud
            last_test:
              status: success
              date: "2026-06-24"
              rto_minutes: 2
        """,
    )

    readings, thresholds = load_pra_tests_yaml(path)

    assert len(readings) == 2
    assert len(thresholds.thresholds) == 2

    by_service = {reading.service: reading for reading in readings}
    assert by_service["gigabyte"].status is None
    assert by_service["nextcloud"].status == "success"
    assert by_service["nextcloud"].tested_at == datetime(
        2026, 6, 24, tzinfo=timezone.utc
    )
    assert by_service["nextcloud"].rto_minutes == 2

    assert thresholds.for_service("gigabyte").max_age_days == 90.0
    assert thresholds.for_service("nextcloud").max_age_days == 90.0


def test_observed_at_is_stamped_as_the_call_is_made(tmp_path: Path):
    path = write(
        tmp_path / "pra_tests.yml",
        """
        max_age_days: 90
        services:
          - name: gigabyte
            last_test: null
        """,
    )

    before = datetime.now(timezone.utc)
    readings, _ = load_pra_tests_yaml(path)
    after = datetime.now(timezone.utc)

    assert before <= readings[0].observed_at <= after


def test_a_definition_missing_max_age_days_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "services: []\n")

    with pytest.raises(ValueError, match="missing: max_age_days"):
        load_pra_tests_yaml(path)


def test_a_definition_missing_services_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "max_age_days: 90\n")

    with pytest.raises(ValueError, match="missing: services"):
        load_pra_tests_yaml(path)


def test_services_that_is_not_a_list_is_refused(tmp_path: Path):
    path = write(tmp_path / "bad.yml", "max_age_days: 90\nservices: not-a-list\n")

    with pytest.raises(ValueError, match="must be a list"):
        load_pra_tests_yaml(path)


def test_a_service_entry_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml", "max_age_days: 90\nservices:\n  - just-a-string\n"
    )

    with pytest.raises(ValueError, match="must be a mapping"):
        load_pra_tests_yaml(path)


def test_a_service_entry_missing_name_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml", "max_age_days: 90\nservices:\n  - last_test: null\n"
    )

    with pytest.raises(ValueError, match="missing: name"):
        load_pra_tests_yaml(path)


def test_a_last_test_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        "max_age_days: 90\nservices:\n  - name: nextcloud\n    last_test: not-a-mapping\n",
    )

    with pytest.raises(ValueError, match="last_test must be a mapping, or null"):
        load_pra_tests_yaml(path)


def test_a_last_test_missing_status_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        (
            "max_age_days: 90\nservices:\n  - name: nextcloud\n"
            "    last_test:\n      date: \"2026-06-24\"\n"
        ),
    )

    with pytest.raises(ValueError, match="missing: status"):
        load_pra_tests_yaml(path)


def test_a_last_test_missing_date_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        (
            "max_age_days: 90\nservices:\n  - name: nextcloud\n"
            "    last_test:\n      status: success\n"
        ),
    )

    with pytest.raises(ValueError, match="missing: date"):
        load_pra_tests_yaml(path)


def test_a_last_test_with_an_invalid_date_is_refused(tmp_path: Path):
    path = write(
        tmp_path / "bad.yml",
        (
            "max_age_days: 90\nservices:\n  - name: nextcloud\n"
            "    last_test:\n      status: success\n      date: \"24/06/2026\"\n"
        ),
    )

    with pytest.raises(ValueError, match="not a YYYY-MM-DD date"):
        load_pra_tests_yaml(path)


def test_a_last_test_may_carry_no_rto(tmp_path: Path):
    path = write(
        tmp_path / "ok.yml",
        (
            "max_age_days: 90\nservices:\n  - name: nextcloud\n"
            "    last_test:\n      status: success\n      date: \"2026-06-24\"\n"
        ),
    )

    readings, _ = load_pra_tests_yaml(path)

    assert readings[0].rto_minutes is None


def test_a_definition_that_is_not_a_mapping_is_refused(tmp_path: Path):
    path = write(tmp_path / "list.yml", "- one\n- two\n")

    with pytest.raises(ValueError, match="mapping"):
        load_pra_tests_yaml(path)


def test_invalid_yaml_syntax_is_reported_as_a_value_error(tmp_path: Path):
    path = write(tmp_path / "broken.yml", "services: [not, valid,\n")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_pra_tests_yaml(path)


def test_the_real_pra_tests_definition_loads():
    """
    `src/aistack/pra/definitions/pra_tests.yml` is not a fixture — it
    is `OPS-0009`'s own declared v1 scope, the file
    `aistack.cli.health_render`/`aistack.cli.console_render` actually
    read. Loading it here means a typo in the real, hand-written file
    is caught by the test suite, the same discipline
    `test_the_real_console_links_definition_loads` already holds.
    """

    repo_root = Path(__file__).resolve().parents[3]

    readings, thresholds = load_pra_tests_yaml(
        repo_root / "src" / "aistack" / "pra" / "definitions" / "pra_tests.yml"
    )

    by_service = {reading.service: reading for reading in readings}
    assert set(by_service) == {
        "gigabyte",
        "raspberry",
        "nextcloud",
        "immich",
        "arrstack",
    }

    # The owner's own real restore-test history, found 2026-09-23 in
    # the legacy `homelab_documentation` engine's own
    # `runtime/pra_tests.json` and carried over here — not invented.
    assert by_service["nextcloud"].status == "success"
    assert by_service["nextcloud"].rto_minutes == 2
    assert by_service["immich"].status == "success"
    assert by_service["immich"].rto_minutes == 5

    # Never tested in that history either — declared the same honest
    # way, not a fabricated success.
    assert by_service["gigabyte"].status is None
    assert by_service["raspberry"].status is None

    # Corrected the same day: a dedicated backup was built
    # (`backup-arrstack.sh`) and a real restore test against it
    # succeeded — `rto_minutes` is the real measured restore time
    # (3m10.7s), rounded down to a whole minute, not a fabricated one.
    assert by_service["arrstack"].status == "success"
    assert by_service["arrstack"].rto_minutes == 3

    for service in by_service:
        assert thresholds.for_service(service).max_age_days == 90.0
