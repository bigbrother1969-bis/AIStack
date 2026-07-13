from pathlib import Path

from aistack.catalog.yaml.store import load_catalog_yaml
from aistack.selection.yaml.store import load_selection_yaml
from aistack.generators.filesystem import generate_copy_folder

catalog = load_catalog_yaml(
    Path("examples/catalogs/music-library-catalog.yml")
)

selection = load_selection_yaml(
    Path("examples/selections/music-android-selection-real.yml")
)

target = Path("/media/TechData/Storage/Music-Android")

generate_copy_folder(
    catalog=catalog,
    selection=selection,
    target_root=target,
    clean=True,
    preserve_names={".stfolder"},
)

print(f"Generated {target}")
