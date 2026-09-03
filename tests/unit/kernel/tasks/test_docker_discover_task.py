"""
`DockerDiscoverTask` — the first production Task the Kernel Runtime
executes (GOV-0002/OS-041, reopened 2026-09-03). Tested in
isolation from the Runtime here; `tests/unit/kernel/bootstrap/
test_tasks.py` covers its registration, and
`tests/unit/cli/test_the_provider_commands_run.py` and
`tests/unit/cli/test_docker_discover_via_kernel_runtime.py` cover
it end to end through `docker_discover.main()`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aistack.kernel.execution import Request
from aistack.kernel.tasks.docker_discover import DockerDiscoverTask


OBSERVATION = {
    "provider": {"id": "aistack.provider.docker"},
    "docker": {"containers": []},
}


class FakeDockerProvider:
    def collect(self) -> dict[str, Any]:
        return OBSERVATION


def test_it_writes_the_observation_the_provider_returns(tmp_path: Path):
    task = DockerDiscoverTask(FakeDockerProvider())
    output_path = tmp_path / "docker-provider-observation.json"

    request = Request(
        request_id="request-001",
        task_id=task.task_id,
        payload={"output_path": str(output_path)},
    )

    task.execute(request)

    assert json.loads(output_path.read_text(encoding="utf-8")) == OBSERVATION


def test_it_keeps_observation_history_like_every_other_generator(tmp_path: Path):
    task = DockerDiscoverTask(FakeDockerProvider())
    output_path = tmp_path / "docker-provider-observation.json"

    request = Request(
        request_id="request-001",
        task_id=task.task_id,
        payload={"output_path": str(output_path)},
    )

    task.execute(request)

    history_dir = output_path.parent / "history" / "docker-provider-observation"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_the_observation_it_returns_carries_the_request_id_and_output_path(
    tmp_path: Path,
):
    task = DockerDiscoverTask(FakeDockerProvider())
    output_path = tmp_path / "docker-provider-observation.json"

    request = Request(
        request_id="request-042",
        task_id=task.task_id,
        payload={"output_path": str(output_path)},
    )

    observation = task.execute(request)

    assert observation.context.request_id == "request-042"
    assert observation.context.component_id == "docker.discover"
    assert observation.data["output_path"] == str(output_path)


def test_a_missing_output_path_in_the_payload_falls_back_to_the_default(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    task = DockerDiscoverTask(FakeDockerProvider())

    request = Request(request_id="request-001", task_id=task.task_id)

    observation = task.execute(request)

    assert observation.data["output_path"] == (
        "reports/generated/docker-provider-observation.json"
    )
    assert (
        tmp_path / "reports" / "generated" / "docker-provider-observation.json"
    ).exists()
