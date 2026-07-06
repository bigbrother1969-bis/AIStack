from pathlib import Path

from catalog_engine.core import Catalog, CatalogItem


class DirectoryCatalogProvider:
    provider_id = "filesystem.directory"

    def __init__(
        self,
        catalog_id: str,
        title: str,
        root: Path,
        max_depth: int = 1,
    ) -> None:
        self.catalog_id = catalog_id
        self.title = title
        self.root = root
        self.max_depth = max_depth

    def collect(self) -> Catalog:
        items: list[CatalogItem] = []

        if not self.root.exists():
            return Catalog(
                catalog_id=self.catalog_id,
                title=self.title,
                items=[],
                metadata={
                    "provider": self.provider_id,
                    "root": str(self.root),
                    "exists": False,
                },
            )

        for path in sorted(self.root.iterdir()):
            if not path.is_dir() or path.name.startswith(".") or path.name == "__pycache__":
                continue

            items.append(
                CatalogItem(
                    id=path.name,
                    label=path.name,
                    kind="directory",
                    source=str(path),
                    metadata={
                        "relative_path": path.name,
                    },
                )
            )

        return Catalog(
            catalog_id=self.catalog_id,
            title=self.title,
            items=items,
            metadata={
                "provider": self.provider_id,
                "root": str(self.root),
                "exists": True,
                "max_depth": self.max_depth,
            },
        )
