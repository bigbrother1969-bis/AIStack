from __future__ import annotations

from aistack.timemachine.graph import Literal
from aistack.timemachine.projection.filter import filter_fact, is_user_data_path


def test_a_path_under_a_declared_root_is_user_data():
    assert is_user_data_path(
        "/mnt/nextcloud/appolonie.persiaut/files/Photos/IMG_1234.jpg",
        ["/mnt/nextcloud"],
    )


def test_the_root_itself_is_user_data():
    assert is_user_data_path("/mnt/nextcloud", ["/mnt/nextcloud"])


def test_a_sibling_that_only_shares_the_prefix_is_not_user_data():
    """
    `"/mnt/nextcloudX"` is a different directory from `"/mnt/
    nextcloud"` even though the string starts the same way — a bare
    prefix match would wrongly catch it.
    """
    assert not is_user_data_path("/mnt/nextcloudX/file.txt", ["/mnt/nextcloud"])


def test_a_path_outside_every_declared_root_is_not_user_data():
    assert not is_user_data_path(
        "/srv/aistack/AIStack/reports/generated/docker-observation.json",
        ["/mnt/nextcloud", "/mnt/immich"],
    )


def test_no_declared_roots_means_nothing_is_user_data():
    """
    The default, 2026-09-27: nothing in this codebase states a real
    root yet, so an empty `user_data_roots` must never drop a fact —
    an empty filter that dropped everything would be indistinguishable
    from a broken one.
    """
    assert not is_user_data_path("/mnt/nextcloud/anything", [])


def test_filter_fact_drops_a_fact_whose_subject_is_user_data():
    assert not filter_fact(
        "/mnt/nextcloud/appolonie.persiaut/files/Photos/IMG_1234.jpg",
        "https://example/container-a",
        ["/mnt/nextcloud"],
    )


def test_filter_fact_drops_a_fact_whose_object_is_user_data():
    assert not filter_fact(
        "https://example/container-a",
        "/mnt/nextcloud/appolonie.persiaut/files/Photos/IMG_1234.jpg",
        ["/mnt/nextcloud"],
    )


def test_filter_fact_never_inspects_a_literal_object_as_a_path():
    """
    A `Literal`'s `.value` is a value, never a reference — even one
    that happens to read like a path is not a fact *about* that path,
    so it is never checked against `user_data_roots`.
    """
    assert filter_fact(
        "https://example/container-a",
        Literal("/mnt/nextcloud/appolonie.persiaut/files/Photos/IMG_1234.jpg"),
        ["/mnt/nextcloud"],
    )


def test_filter_fact_keeps_an_ordinary_fact():
    assert filter_fact(
        "https://example/container-a",
        "https://example/collector-run-1",
        ["/mnt/nextcloud"],
    )
