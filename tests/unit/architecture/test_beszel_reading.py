from aistack.architecture.beszel_reading import build_beszel_readings


def real_gigabyte_record() -> dict:
    """
    The exact shape the owner's own hub returned, 2026-09-12 — not a
    hypothetical fixture. `t`/`p`/`os`/`bb`/`ct` are deliberately
    present here (as the real API sends them) even though this
    module does not surface them, so the tests prove they are
    ignored rather than assumed absent.
    """

    return {
        "collectionId": "2hz5ncl8tizk5nx",
        "collectionName": "systems",
        "created": "2026-06-16 11:51:22.468Z",
        "host": "192.168.1.10",
        "id": "zdj5eona5jgqw7o",
        "info": {
            "t": 4,
            "u": 241495,
            "cpu": 17.42,
            "mp": 67.74,
            "dp": 72.22,
            "v": "0.19.0",
            "p": False,
            "g": 0,
            "dt": 68.25,
            "os": 0,
            "bb": 125897,
            "la": [0.4, 0.69, 0.87],
            "ct": 1,
        },
        "name": "Gigabyte",
        "port": "45876",
        "status": "up",
        "updated": "2026-09-12 10:55:55.987Z",
        "users": ["q6bpa5zceh2mrpx"],
    }


# --------------------------------------------------------------------
# The real record, exactly as Beszel returned it
# --------------------------------------------------------------------


def test_the_real_gigabyte_record_reads_correctly():
    readings = build_beszel_readings([real_gigabyte_record()])

    assert len(readings) == 1
    reading = readings[0]

    assert reading.name == "Gigabyte"
    assert reading.host == "192.168.1.10"
    assert reading.status == "up"
    assert reading.cpu_pct == 17.42
    assert reading.mem_pct == 67.74
    assert reading.disk_pct == 72.22
    assert reading.temp_c == 68.25
    assert reading.load_avg == (0.4, 0.69, 0.87)
    assert reading.uptime_seconds == 241495


def test_several_systems_travel_in_order():
    raspberry = real_gigabyte_record() | {"name": "Raspberry pi", "host": "192.168.1.40"}
    gigabyte = real_gigabyte_record()

    readings = build_beszel_readings([raspberry, gigabyte])

    assert [r.name for r in readings] == ["Raspberry pi", "Gigabyte"]


# --------------------------------------------------------------------
# Fields this project does not surface never reach `BeszelSystemReading`
# --------------------------------------------------------------------


def test_the_reading_carries_no_unsurfaced_fields():
    reading = build_beszel_readings([real_gigabyte_record()])[0]

    surfaced = {
        "name",
        "host",
        "status",
        "cpu_pct",
        "mem_pct",
        "disk_pct",
        "temp_c",
        "load_avg",
        "uptime_seconds",
    }
    assert {f.name for f in type(reading).__dataclass_fields__.values()} == surfaced


# --------------------------------------------------------------------
# Tolerance — a live third-party API, not a hand-written YAML
# --------------------------------------------------------------------


def test_not_a_list_at_all_reads_as_no_systems():
    assert build_beszel_readings(None) == ()
    assert build_beszel_readings({"items": []}) == ()
    assert build_beszel_readings("not a list") == ()


def test_a_non_mapping_item_is_skipped_not_raised():
    readings = build_beszel_readings(["not a dict", real_gigabyte_record()])

    assert len(readings) == 1
    assert readings[0].name == "Gigabyte"


def test_an_item_with_no_name_is_skipped():
    item = real_gigabyte_record()
    del item["name"]

    assert build_beszel_readings([item]) == ()


def test_an_item_with_an_empty_name_is_skipped():
    item = real_gigabyte_record() | {"name": ""}

    assert build_beszel_readings([item]) == ()


def test_a_missing_host_reads_as_empty_string():
    item = real_gigabyte_record()
    del item["host"]

    reading = build_beszel_readings([item])[0]
    assert reading.host == ""


def test_a_missing_status_reads_as_empty_string():
    item = real_gigabyte_record()
    del item["status"]

    reading = build_beszel_readings([item])[0]
    assert reading.status == ""


def test_a_missing_info_object_reads_every_metric_as_none():
    item = real_gigabyte_record()
    del item["info"]

    reading = build_beszel_readings([item])[0]

    assert reading.cpu_pct is None
    assert reading.mem_pct is None
    assert reading.disk_pct is None
    assert reading.temp_c is None
    assert reading.load_avg is None
    assert reading.uptime_seconds is None


def test_info_fields_beszels_own_omitempty_leaves_out_read_as_none():
    """
    Beszel's own `Info` struct marks almost every numeric field
    `omitempty`/`omitzero` — a system with nothing to report for
    temperature (a VM, no sensor) simply omits `dt` rather than
    sending `0`. This is exactly what the real Pi-hole record looked
    like, 2026-09-12: no `dt` key at all.
    """

    item = real_gigabyte_record()
    del item["info"]["dt"]
    del item["info"]["la"]

    reading = build_beszel_readings([item])[0]

    assert reading.temp_c is None
    assert reading.load_avg is None
    # Everything else on the same record still travels.
    assert reading.cpu_pct == 17.42


def test_a_load_average_that_is_not_exactly_three_numbers_is_none():
    item = real_gigabyte_record()
    item["info"]["la"] = [0.4, 0.69]

    reading = build_beszel_readings([item])[0]
    assert reading.load_avg is None


def test_a_load_average_containing_a_non_number_is_none():
    item = real_gigabyte_record()
    item["info"]["la"] = [0.4, "oops", 0.87]

    reading = build_beszel_readings([item])[0]
    assert reading.load_avg is None


def test_a_boolean_where_a_number_is_expected_is_not_mistaken_for_one():
    """
    `bool` is a subclass of `int` in Python — `isinstance(True, int)`
    is `True` — so this is checked explicitly rather than trusted to
    fall out of `isinstance(value, (int, float))` naturally.
    """

    item = real_gigabyte_record()
    item["info"]["cpu"] = True

    reading = build_beszel_readings([item])[0]
    assert reading.cpu_pct is None


def test_an_integer_uptime_stays_an_integer():
    item = real_gigabyte_record()
    item["info"]["u"] = 100

    reading = build_beszel_readings([item])[0]
    assert reading.uptime_seconds == 100
    assert isinstance(reading.uptime_seconds, int)
