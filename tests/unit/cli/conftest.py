from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_real_docker_events_history(monkeypatch):
    """
    The Services domain's restart-loop check reads the docker-events
    history under `reports/generated/` relative to the working
    directory — on the reference host that is the real, live history.
    No CLI test may depend on it: every test here sees an empty one
    unless it patches its own.
    """

    monkeypatch.setattr(
        "aistack.runtime.restart_loop.read_recent_docker_events",
        lambda since, output_path=None: [],
    )
