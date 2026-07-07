from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from aistack.selection.core import Selection


def save_selection_yaml(selection: Selection, path: Path) -> Path:
    """Save a governed selection to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(asdict(selection), stream, sort_keys=False, allow_unicode=True)
    return path
