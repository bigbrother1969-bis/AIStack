from pathlib import Path
import yaml

from selection_engine.core import Selection


def save_selection(selection: Selection, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "selection_id": selection.selection_id,
        "catalog_id": selection.catalog_id,
        "selected_ids": sorted(selection.selected_ids),
        "metadata": selection.metadata,
    }

    target.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_selection(source: Path) -> Selection | None:
    if not source.exists():
        return None

    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}

    return Selection(
        selection_id=data["selection_id"],
        catalog_id=data["catalog_id"],
        selected_ids=data.get("selected_ids", []),
        metadata=data.get("metadata", {}),
    )
