from pathlib import Path

from catalog_engine.providers.filesystem import DirectoryCatalogProvider
from catalog_engine.yaml_store import save_catalog


MUSIC_ROOT = Path("/media/TechData/Storage/Music")

provider = DirectoryCatalogProvider(
    catalog_id="music-library",
    title="Music Library",
    root=MUSIC_ROOT,
)

catalog = provider.collect()

out = Path("examples/catalog_engine/music-library-catalog.yml")
save_catalog(catalog, out)

print(f"Generated: {out}")
print(f"Items: {len(catalog.items)}")
