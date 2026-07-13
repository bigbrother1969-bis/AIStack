from pathlib import Path

from selection_engine.core import Selection, SelectionCatalog, SelectionItem
from selection_engine.yaml_store import save_selection


catalog = SelectionCatalog(
    catalog_id="music-library",
    title="Music Library",
    items=[
        SelectionItem(id="pink-floyd", label="Pink Floyd"),
        SelectionItem(id="queen", label="Queen"),
        SelectionItem(id="acdc", label="AC/DC"),
    ],
    metadata={"source": "demo"},
)

selection = Selection(
    selection_id="music-android",
    catalog_id=catalog.catalog_id,
    selected_ids=["pink-floyd", "queen"],
    metadata={
        "target": "android",
        "mode": "directory-selection",
    },
)

out = Path("examples/selection_engine/music-android-selection.yml")
save_selection(selection, out)

print(f"Generated: {out}")
