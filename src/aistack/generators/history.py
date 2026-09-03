from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def write_artifact_with_history(content: str, latest_path: Path) -> tuple[Path, Path]:
    """
    Write a generated artifact both to its stable path and to a
    timestamped copy that nothing else touches — Observation
    History, the first piece of the multi-orthogonal historisation
    workstream the owner opened 2026-09-03
    (`docs/99-meta/roadmap/AIStack-Medium-Term-Development-Roadmap.md`
    § *Knowledge Time Machine*, `claude/ROADMAP-SYNTHESIS-2026-09-03.md`).

    **The defect this closes.** All four provider-CLI generators
    (`DockerObservationArtifactGenerator`, `DockerCatalogArtifactGenerator`,
    `ComposeCatalogArtifactGenerator`, `CatalogViewArtifactGenerator`)
    wrote to one fixed path with a plain `write_text`, so every run
    destroyed the previous observation. Not merely absent — actively
    discarded, on every execution, for as long as the four commands
    have existed.

    **The shape, decided with the owner 2026-09-03.** Every
    observation is kept, indefinitely — no retention window, no
    count cap: this is what makes it a history rather than a rolling
    buffer, and `reports/generated/` is already gitignored (ENG-P-003
    disposable), so keeping every copy costs host disk, not governed
    heritage. `latest_path` keeps writing exactly what it always did,
    so every existing reader — the four `tests/unit/cli/
    test_the_provider_commands_run.py` tests among them — sees no
    change. The timestamped copy lives in a `history/<stem>/`
    subdirectory beside it, one per artifact kind, so
    `reports/generated/` does not fill with hundreds of same-named
    files as the four commands are run over time.

    **The timestamp is `strftime`, not the `isoformat` this
    heritage otherwise uses** (`generators/filesystem/yaml/store.py`'s
    own `generated_at`) — a filesystem path cannot carry `:`, and an
    ISO timestamp carries three.

    **A second-resolution timestamp collides.** Found by this
    module's own test, calling this function twice in the same
    process: two writes inside the same second produced the same
    filename, and the second silently overwrote the first — the
    exact loss "keep everything, indefinitely" was decided against.
    A numeric suffix disambiguates rather than raising or waiting
    out the clock, so the guarantee holds regardless of how close
    together two calls land.
    """

    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(content, encoding="utf-8")

    history_dir = latest_path.parent / "history" / latest_path.stem
    history_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    history_path = history_dir / f"{stamp}{latest_path.suffix}"
    suffix = 1
    while history_path.exists():
        history_path = history_dir / f"{stamp}-{suffix}{latest_path.suffix}"
        suffix += 1
    history_path.write_text(content, encoding="utf-8")

    return latest_path, history_path
