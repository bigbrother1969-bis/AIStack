from __future__ import annotations

import base64

from aistack.renderers.architecture.icons import load_icon_data_uri


def test_a_none_key_resolves_to_none():
    assert load_icon_data_uri(None) is None


def test_an_empty_key_resolves_to_none():
    assert load_icon_data_uri("") is None


def test_an_unknown_key_resolves_to_none_rather_than_raising():
    """
    A typo in `service_categorization.yml`, or an icon removed from
    `vendor/icons/` without updating it, must not crash the whole
    render — the same "nothing to look up" treatment
    `ServiceNode.container is None` already gets in `graph.py`.
    """

    assert load_icon_data_uri("this-icon-does-not-exist") is None


def test_a_known_png_key_resolves_to_a_base64_png_data_uri():
    data_uri = load_icon_data_uri("pi-hole")

    assert data_uri is not None
    assert data_uri.startswith("data:image/png;base64,")

    encoded = data_uri.removeprefix("data:image/png;base64,")
    decoded = base64.b64decode(encoded)
    assert decoded.startswith(b"\x89PNG\r\n\x1a\n")


def test_a_known_svg_key_resolves_to_a_base64_svg_data_uri():
    data_uri = load_icon_data_uri("router-wireless")

    assert data_uri is not None
    assert data_uri.startswith("data:image/svg+xml;base64,")

    encoded = data_uri.removeprefix("data:image/svg+xml;base64,")
    decoded = base64.b64decode(encoded)
    assert b"<svg" in decoded


def test_every_icon_key_the_real_categorization_declares_resolves():
    """
    Not a fixture round-trip — every `icon:` value the real, shipped
    `service_categorization.yml` declares must resolve to a real
    vendored file, or `architecture.html` silently ships the
    placeholder for it. A typo here is exactly the class of defect
    `test_the_real_service_categorization_loads` already guards for
    `container` — this is that same guard for `icon`.
    """

    from pathlib import Path

    from aistack.architecture.yaml import load_service_categorization_yaml

    repo_root = Path(__file__).resolve().parents[4]
    definition = load_service_categorization_yaml(
        repo_root
        / "src"
        / "aistack"
        / "architecture"
        / "definitions"
        / "service_categorization.yml"
    )

    missing = [
        service.name
        for category in definition.categories
        for service in category.services
        if service.icon and load_icon_data_uri(service.icon) is None
    ]

    assert missing == []
