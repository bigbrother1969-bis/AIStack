from __future__ import annotations

import sys
from collections.abc import Mapping
from typing import Any
import time
from datetime import datetime
from pathlib import Path

from aistack.ai_runtime import compare
from aistack.ai_runtime.call_journal import AI_COMPARE, journaled
from aistack.ai_runtime.policy import EXTERNAL, current_policy
from aistack.ai_runtime.definition import LocalEngineDefinition
from aistack.ai_runtime.operations import _LANGUAGE_DIRECTIVE
from aistack.ai_runtime.yaml import load_ai_runtime_yaml
from aistack.contracts.ai_runtime_answer import AIRuntimeAnswer
from aistack.generators.ai_compare import AiCompareReportArtifactGenerator
from aistack.i18n import translator_for
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.security import screen, series
from aistack.tasks.security_assess import DEFAULT_GENERATED_DIR
from aistack.troubleshooting.guide import AI_RUNTIME, OPERATIONS, ask_one


class AiCompareTask:
    """
    Put the local engines side by side on the findings of the last security
    report (`ai.compare`, ADR-0028 slice T4b, the test of a second engine).

    It asks what the Security page asks (the fixed texts and the cleaned
    evidence), each engine alone and in turn, and writes the answers, their
    times and a few automatic flags as markdown under `ai-compare/` of the
    data directory. Nothing on any host is changed, no engine that can leave
    the network is asked, and the payload carries no secret.

    The payload says which engines (`engines`: specs, else those of
    `ai_runtime.yml`), which findings (`findings`: keys, else the `max` worst),
    the `language`, the `operations`, where the data is (`generated_dir`) and
    whether it is only a `dry_run`.

    Returns an Observation of plain values: what was asked, where the report
    went, and the reason when nothing could be asked.
    """

    task_id = "ai.compare"
    task_name = "AI engines comparison"

    def execute(self, request: Request) -> Observation:
        data = self._compare(request.payload)
        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data=data,
        )

    def _compare(self, payload: Mapping[str, Any]) -> dict[str, object]:
        generated = Path(str(payload.get("generated_dir", DEFAULT_GENERATED_DIR)))
        language = str(payload.get("language", "fr"))
        operations = [str(name) for name in payload.get("operations") or OPERATIONS]

        try:
            specs = [str(spec) for spec in payload.get("engines") or []]
            engines = [compare.parse_engine(spec) for spec in specs] or list(load_ai_runtime_yaml(AI_RUNTIME).local_engines())
            unknown = [name for name in operations if name not in OPERATIONS]
            if unknown:
                raise ValueError(f"unknown operation {unknown[0]!r} (one of {', '.join(OPERATIONS)})")
            if language not in _LANGUAGE_DIRECTIVE:
                raise ValueError(f"unknown language {language!r} (one of {', '.join(sorted(_LANGUAGE_DIRECTIVE))})")
        except ValueError as error:
            return _refused(str(error))
        if not engines:
            return _refused("no engine to compare: declare `engines:` in ai_runtime.yml or give --engine")

        report = series.read_report(generated)
        if report is None:
            return _refused(f"no readable security report under {generated}")

        t = translator_for(language)
        keys = [str(key) for key in payload.get("findings") or []]
        if keys:
            by_key = {str(item["key"]): item for item in screen.findings_of(report)}
            missing = [key for key in keys if key not in by_key]
            if missing:
                return _refused(f"no finding {missing[0]!r} in the report")
            chosen = [screen.row_of(by_key[key]) for key in keys]
        else:
            chosen = screen.rows(report, False, {})[: max(int(str(payload.get("max", 2))), 0)]
        if not chosen:
            return _refused("no finding to watch or worse in the report; name one with --finding")

        # The comparison is a use like another (`ADR-0029`): declared internal, it asks no engine outside.
        policy = current_policy()
        if not policy.allows_external(AI_COMPARE):
            outside = [engine for engine in engines if policy.kind_of_host(engine.host) == EXTERNAL]
            if outside:
                return _refused(
                    f"{compare.name_of(outside[0])} is outside your machines and {AI_COMPARE} is internal_only "
                    f"in ai_policy.yml (declare it external_allowed, or list the host in internal_hosts)"
                )

        subjects = [compare.Subject(row.key, row.title, screen.facts_for_engine(row, t), screen.runtime_finding(row, t)) for row in chosen]
        summary: dict[str, object] = {
            "refused": "",
            "engines": [compare.name_of(engine) for engine in engines],
            "findings": [subject.key for subject in subjects],
            "questions": len(engines) * len(subjects) * len(operations),
            "operations": operations,
            "dry_run": bool(payload.get("dry_run")),
            "report_path": "",
        }
        if summary["dry_run"]:
            return summary

        def ask(engine: LocalEngineDefinition, subject: compare.Subject, operation: str) -> AIRuntimeAnswer:
            return journaled(ask_one, AI_COMPARE, generated / "ai-calls")(
                engine, subject.finding, operation, language, subject.context
            )

        outcomes = compare.run(
            engines, subjects, operations, language, ask, time.monotonic,
            progress=lambda line: print("  " + line, file=sys.stderr, flush=True),
        )
        text = compare.render_markdown(outcomes, subjects, engines, language, datetime.now())
        _latest, kept = AiCompareReportArtifactGenerator().generate(text, generated / "ai-compare" / "compare.md")
        summary["report_path"] = str(kept)
        return summary


def _refused(reason: str) -> dict[str, object]:
    return {"refused": reason, "engines": [], "findings": [], "questions": 0, "operations": [], "dry_run": False, "report_path": ""}
