"""How old the running containers' images are, read locally (ADR-0028 T2b)."""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import INFORMATION, WATCH
from aistack.security.hygiene import OLD_IMAGE, Container, parse_inspect, propose_accepted
from aistack.security.images import assess_images, old_images, parse_created, read_created

NOW = datetime(2026, 11, 19, 20, 0, tzinfo=timezone.utc)


def _container(name: str, image_id: str) -> Container:
    return Container(name=name, image=f"{name}:latest", risks=frozenset(), host_network=False, image_id=image_id)


def _built(days: int) -> datetime:
    return NOW - timedelta(days=days)


def test_docker_dates_with_nanoseconds_are_read() -> None:
    found = parse_created("sha256:aa 2025-10-01T12:00:00.123456789Z\nsha256:bb 2025-10-01T12:00:00Z\nbroken\nsha256:cc nonsense\n")

    assert found == {
        "sha256:aa": datetime(2025, 10, 1, 12, 0, 0, 123456, tzinfo=timezone.utc),
        "sha256:bb": datetime(2025, 10, 1, 12, 0, tzinfo=timezone.utc),
    }


def test_the_image_id_of_a_container_is_read_from_inspect() -> None:
    containers = parse_inspect('[{"Name": "/a", "Image": "sha256:aa", "Config": {"Image": "a"}}]')

    assert containers is not None and containers[0].image_id == "sha256:aa"


def test_an_old_image_is_to_watch_with_its_age_oldest_first() -> None:
    containers = [_container("young", "a"), _container("old", "b"), _container("older", "c")]
    created = {"a": _built(30), "b": _built(400), "c": _built(900)}

    findings = assess_images(containers, created, NOW, SecurityDefinition())

    assert [(finding.key, finding.severity) for finding in findings] == [("images.old", WATCH)]
    assert findings[0].evidence == ("older (older:latest): 900 days", "old (old:latest): 400 days")
    assert "no registry is asked" in findings[0].unknown


def test_the_limit_is_the_owners() -> None:
    containers = [_container("a", "a")]

    assert assess_images(containers, {"a": _built(100)}, NOW, SecurityDefinition(max_image_age_days=90))[0].key == "images.old"
    assert assess_images(containers, {"a": _built(100)}, NOW, SecurityDefinition(max_image_age_days=365)) == []


def test_an_accepted_old_image_is_counted_not_reported() -> None:
    containers = [_container("finished", "a"), _container("other", "b")]
    created = {"a": _built(800), "b": _built(800)}
    definition = SecurityDefinition(accepted={OLD_IMAGE: ("finished",)})

    findings = {finding.key: finding for finding in assess_images(containers, created, NOW, definition)}

    assert findings["images.old"].evidence == ("other (other:latest): 800 days",)
    assert findings["images.accepted"].severity == INFORMATION and findings["images.accepted"].evidence == ("finished",)


def test_images_that_could_not_be_read_are_a_finding_never_an_absence() -> None:
    assert [finding.key for finding in assess_images([_container("a", "a")], None, NOW, SecurityDefinition())] == ["images.unreadable"]
    assert assess_images([], None, NOW, SecurityDefinition()) == []
    assert assess_images(None, None, NOW, SecurityDefinition()) == []


def test_docker_is_asked_once_for_all_the_images_and_failure_is_none() -> None:
    asked: list[list[str]] = []

    def run(command, **_):
        asked.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="a 2025-01-01T00:00:00Z\n")

    assert set(read_created(["a", "b"], run) or {}) == {"a"}
    assert asked == [["docker", "image", "inspect", "--format", "{{.Id}} {{.Created}}", "a", "b"]]
    assert read_created([]) == {}
    assert read_created(["a"], lambda command, **_: subprocess.CompletedProcess(command, 1, stdout="")) is None


def test_the_proposal_includes_the_old_images() -> None:
    containers = [_container("finished", "a")]
    old = old_images(containers, {"a": _built(800)}, NOW, SecurityDefinition())

    text = propose_accepted(containers, SecurityDefinition(), {OLD_IMAGE: [item.name for item, _ in old]})

    assert text == "accepted:\n  old_image:\n    - finished\n"
