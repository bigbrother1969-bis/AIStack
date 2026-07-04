from pathlib import Path

from catalog_engine.providers.filesystem import DirectoryCatalogProvider
from catalog_engine.yaml_store import save_catalog


provider = DirectoryCatalogProvider(
    catalog_id="demo-directory-catalog",
    title="Demo Directory Catalog",
    root=Path("examples"),
)

catalog = provider.collect()

out = Path("examples/catalog_engine/demo-directory-catalog.yml")
save_catalog(catalog, out)

print(f"Generated: {out}")
print(f"Items: {len(catalog.items)}")
