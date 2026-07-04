from pathlib import Path

from catalog_engine.yaml_store import load_catalog
from selection_engine.yaml_store import load_selection
from generation_engine.generators.filesystem_selection import generate_symlink_folder


catalog = load_catalog(Path("examples/catalog_engine/music-library-catalog.yml"))
selection = load_selection(Path("examples/selection_engine/music-android-selection-real.yml"))

if selection is None:
    raise SystemExit("Missing selection file")

target = Path("/media/TechData/Storage/Music-Android")

generate_symlink_folder(
    catalog=catalog,
    selection=selection,
    target_root=target,
    clean=True,
)

print(f"Generated folder: {target}")
