from aistack.architecture.http_probe_reading import build_http_probe_readings


def real_target(**overrides) -> dict:
    """
    The exact shape `HttpProbeProvider.collect()["http_probe"]
    ["targets"]` produces for one target — not a hypothetical
    fixture.
    """

    base = {
        "name": "Gitea",
        "url": "https://gitea.persiaut-family.fr",
        "reachable": True,
        "status_code": 200,
        "unreachable_reason": "",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------
# The real record, exactly as the provider produced it
# --------------------------------------------------------------------


def test_a_reachable_target_reads_correctly():
    readings = build_http_probe_readings([real_target()])

    assert len(readings) == 1
    reading = readings[0]

    assert reading.name == "Gitea"
    assert reading.url == "https://gitea.persiaut-family.fr"
    assert reading.reachable is True
    assert reading.status_code == 200
    assert reading.unreachable_reason == ""


def test_an_unreachable_target_reads_correctly():
    item = real_target(
        reachable=False,
        status_code=None,
        unreachable_reason="https://gitea.persiaut-family.fr could not be reached: timed out",
    )

    reading = build_http_probe_readings([item])[0]

    assert reading.reachable is False
    assert reading.status_code is None
    assert "could not be reached" in reading.unreachable_reason


def test_several_targets_travel_in_order():
    readings = build_http_probe_readings(
        [real_target(name="Gitea"), real_target(name="Vaultwarden")]
    )

    assert [r.name for r in readings] == ["Gitea", "Vaultwarden"]


# --------------------------------------------------------------------
# Tolerance — this project's own provider output, not a hand-written YAML
# --------------------------------------------------------------------


def test_not_a_list_at_all_reads_as_no_targets():
    assert build_http_probe_readings(None) == ()
    assert build_http_probe_readings({"targets": []}) == ()
    assert build_http_probe_readings("not a list") == ()


def test_a_non_mapping_item_is_skipped_not_raised():
    readings = build_http_probe_readings(["not a dict", real_target()])

    assert len(readings) == 1
    assert readings[0].name == "Gitea"


def test_an_item_with_no_name_is_skipped():
    item = real_target()
    del item["name"]

    assert build_http_probe_readings([item]) == ()


def test_an_item_with_an_empty_name_is_skipped():
    item = real_target(name="")

    assert build_http_probe_readings([item]) == ()


def test_a_missing_url_reads_as_empty_string():
    item = real_target()
    del item["url"]

    reading = build_http_probe_readings([item])[0]
    assert reading.url == ""


def test_a_missing_reachable_flag_reads_as_false():
    item = real_target()
    del item["reachable"]

    reading = build_http_probe_readings([item])[0]
    assert reading.reachable is False


def test_a_non_boolean_reachable_flag_reads_as_false():
    item = real_target(reachable="yes")

    reading = build_http_probe_readings([item])[0]
    assert reading.reachable is False


def test_a_missing_status_code_reads_as_none():
    item = real_target()
    del item["status_code"]

    reading = build_http_probe_readings([item])[0]
    assert reading.status_code is None


def test_a_boolean_status_code_is_not_mistaken_for_an_integer():
    """
    `bool` is a subclass of `int` in Python — checked explicitly, same
    defensive reasoning `build_beszel_readings` already applies to its
    own numeric fields.
    """

    item = real_target(status_code=True)

    reading = build_http_probe_readings([item])[0]
    assert reading.status_code is None


def test_a_missing_unreachable_reason_reads_as_empty_string():
    item = real_target()
    del item["unreachable_reason"]

    reading = build_http_probe_readings([item])[0]
    assert reading.unreachable_reason == ""
