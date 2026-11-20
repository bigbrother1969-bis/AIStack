from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aistack.config import PACKAGE_ROOT, configured
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.security import window
from aistack.security.yaml import load_security_yaml

DEFAULT_GENERATED_DIR = "reports/generated"
DEFAULT_DEFINITION = configured(PACKAGE_ROOT / "security" / "definitions" / "security.yml")

OPEN, END, SHOW = "open", "end", "show"


class SecurityWindowTask:
    """
    The maintenance window (`security.window`, ADR-0028 slice T4a).

    The owner says he is working on the hosts for a while: for that time the
    vigil counts the drift of files and units and does not tell Gotify about
    it. The payload's `action` is `open` (with `minutes`), `end` or `show`;
    `generated_dir` says where the window's two small files live. It changes
    nothing on any host.

    Returns an Observation of plain values: whether the action was taken
    (`ok`, and `error` when it was refused), whether a window is open, until
    when, how many minutes are left, and the owner's time zone.
    """

    task_id = "security.window"
    task_name = "Maintenance window"

    def execute(self, request: Request) -> Observation:
        generated_dir = Path(request.payload.get("generated_dir", DEFAULT_GENERATED_DIR))
        action = str(request.payload.get("action", SHOW))
        definition = load_security_yaml(DEFAULT_DEFINITION)
        now = datetime.now(timezone.utc)
        ok, error, ended = True, "", False

        if action == OPEN:
            try:
                window.open_window(
                    generated_dir, now, window.parse_duration(str(request.payload.get("duration", ""))), definition.window_max_hours
                )
            except ValueError as refusal:
                ok, error = False, str(refusal)
        elif action == END:
            ended = window.end(generated_dir, now)
        elif action != SHOW:
            ok, error = False, f"unknown action: {action}"

        opened = window.current(generated_dir, now)

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "ok": ok,
                "error": error,
                "ended": ended,
                "open": opened is not None,
                "until": opened.until.isoformat(timespec="seconds") if opened else "",
                "minutes_left": int(opened.remaining(now).total_seconds() // 60) if opened else 0,
                "zone": definition.digest_timezone,
            },
        )
