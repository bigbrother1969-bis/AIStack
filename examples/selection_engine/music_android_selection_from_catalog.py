from pathlib import Path

from catalog_engine.yaml_store import load_catalog
from selection_engine.core import Selection
from selection_engine.yaml_store import save_selection


catalog_path = Path("examples/catalog_engine/music-library-catalog.yml")
catalog = load_catalog(catalog_path)

wanted_labels = {
    "Air",
    "Alain Bashung",
    "AC  DC",
}

available_ids = {item.id for item in catalog.items}
selected_ids = sorted(item_id for item_id in wanted_labels if item_id in available_ids)

selection = Selection(
    selection_id="music-android",
    catalog_id=catalog.catalog_id,
    selected_ids=selected_ids,
    metadata={
        "target": "android",
        "mode": "directory-selection",
        "source_catalog": str(catalog_path),
    },
)

out = Path("examples/selection_engine/music-android-selection-real.yml")
save_selection(selection, out)

print(f"Generated: {out}")
print(f"Selected: {len(selected_ids)}")
for item_id in selected_ids:
    print(f"- {item_id}")
