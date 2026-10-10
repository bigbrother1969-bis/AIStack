"""Every container docker-compose.yml starts is declared in the shipped
service_categorization.yml — else AIStack's own containers are an
inventory gap on the reference host (aistack-vigil, 2026-10-09)."""

from __future__ import annotations

from pathlib import Path

import yaml

from aistack.architecture.yaml import load_service_categorization_yaml

ROOT = Path(__file__).resolve().parents[3]


def test_every_compose_container_is_declared() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    started = {
        service["container_name"]
        for service in compose["services"].values()
        if "container_name" in service
    }
    shipped = Path(__file__).resolve().parents[2] / "reference" / "definitions" / "service_categorization.yml"
    categorization = load_service_categorization_yaml(shipped)
    text = shipped.read_text(encoding="utf-8")
    assert started
    missing = sorted(name for name in started if f"container: {name}\n" not in text)
    assert missing == [], missing
    assert categorization is not None
