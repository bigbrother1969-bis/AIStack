from __future__ import annotations

from pathlib import Path

from aistack.catalog.yaml import load_catalog_yaml
from aistack.catalog.views.music import MusicSelectionViewEngine
from aistack.selection.core import Selection
from aistack.selection.yaml import save_selection_yaml


catalog_path = Path("examples/catalog_engine/music-library-catalog.yml")
catalog = load_catalog_yaml(catalog_path)

wanted_labels = {
    "Air",
    "Alain Bashung",
    "AC  DC",
}

view = MusicSelectionViewEngine().build(catalog)
available_ids = {item.id for item in view.items}
selected_ids = sorted(item_id for item_id in wanted_labels if item_id in available_ids)

selection = Selection(
    selection_id="music-android",
    catalog_id=catalog.catalog_id,
    selected_ids=selected_ids,
    metadata={
        "target": "android",
        "mode": "directory-selection",
        "sync_engine": "syncthing",
        "source_catalog": str(catalog_path),
    },
)

out = Path("reports/generated/music-android-selection-test.yml")
save_selection_yaml(selection, out)

print(f"Generated: {out}")
print(f"Selected: {len(selected_ids)}")
for item_id in selected_ids:
    print(f"- {item_id}")
