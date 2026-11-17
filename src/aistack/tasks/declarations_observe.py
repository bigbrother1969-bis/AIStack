from __future__ import annotations

from pathlib import Path

from aistack.config import config_dir, shipped_definitions
from aistack.declaration.observe import observe
from aistack.kernel.execution import Observation, ObservationContext, Request

DEFAULT_GENERATED_DIR = "reports/generated"


class DeclarationsObserveTask:
    """
    Look for the declarations edited by hand on the host
    (`declarations.observe`, `ADR-0027` § 12).

    The seventh chain the Runtime executes. It compares each shipped
    declaration's file in the configuration directory with the snapshot of
    it that the data directory holds, and says which differ and how:
    `reference` (first sight), `follow` (a screen wrote it) or `edited`
    (by hand). It writes nothing and returns digests, never content: moving
    the snapshots and recording the edits is `aistack.declaration.observe.apply`,
    through the transaction service.

    The request payload's `generated_dir` (default `reports/generated`) is
    the data directory; `config_dir` defaults to `AISTACK_CONFIG_DIR`. With
    neither, there is nothing to observe: a development checkout reads the
    shipped files.
    """

    task_id = "declarations.observe"
    task_name = "Declarations observe"

    def execute(self, request: Request) -> Observation:
        generated_dir = Path(request.payload.get("generated_dir", DEFAULT_GENERATED_DIR))
        given = str(request.payload.get("config_dir", "")).strip()
        directory = Path(given) if given else config_dir()
        changes = observe(directory, generated_dir, shipped_definitions()) if directory is not None else []

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "config_dir": str(directory) if directory is not None else "",
                "generated_dir": str(generated_dir),
                "changes": [
                    {"name": item.name, "kind": item.kind, "before": item.before, "after": item.after}
                    for item in changes
                ],
            },
        )
