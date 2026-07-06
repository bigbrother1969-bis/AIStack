from pathlib import Path
import yaml

from catalog_engine.core import Catalog, CatalogItem


def save_catalog(catalog: Catalog, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "catalog_id": catalog.catalog_id,
        "title": catalog.title,
        "metadata": catalog.metadata,
        "items": [
            {
                "id": item.id,
                "label": item.label,
                "kind": item.kind,
                "source": item.source,
                "metadata": item.metadata,
            }
            for item in catalog.items
        ],
    }

    target.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_catalog(source: Path) -> Catalog:
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}

    return Catalog(
        catalog_id=data["catalog_id"],
        title=data["title"],
        metadata=data.get("metadata", {}),
        items=[
            CatalogItem(
                id=item["id"],
                label=item["label"],
                kind=item["kind"],
                source=item["source"],
                metadata=item.get("metadata", {}),
            )
            for item in data.get("items", [])
        ],
    )
