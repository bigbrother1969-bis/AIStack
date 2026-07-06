from pathlib import Path
import shutil

from catalog_engine.core import Catalog
from selection_engine.core import Selection


def generate_symlink_folder(
    catalog: Catalog,
    selection: Selection,
    target_root: Path,
    clean: bool = True,
) -> None:
    target_root.mkdir(parents=True, exist_ok=True)

    if clean:
        for child in target_root.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)

    items_by_id = {item.id: item for item in catalog.items}

    for selected_id in selection.selected_ids:
        item = items_by_id.get(selected_id)

        if item is None:
            print(f"SKIP missing catalog item: {selected_id}")
            continue

        source = Path(item.source)
        target = target_root / item.label

        if target.exists() or target.is_symlink():
            target.unlink()

        target.symlink_to(source, target_is_directory=True)
        print(f"LINK {target} -> {source}")

def generate_copy_folder(
    catalog: Catalog,
    selection: Selection,
    target_root: Path,
    clean: bool = True,
    preserve_names: set[str] | None = None,
) -> None:
    preserve_names = preserve_names or set()
    target_root.mkdir(parents=True, exist_ok=True)

    if clean:
        for child in target_root.iterdir():
            if child.name in preserve_names:
                continue
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)

    items_by_id = {item.id: item for item in catalog.items}

    for selected_id in selection.selected_ids:
        item = items_by_id.get(selected_id)

        if item is None:
            print(f"SKIP missing catalog item: {selected_id}")
            continue

        source = Path(item.source)
        target = target_root / item.label

        if not source.exists():
            print(f"SKIP missing source: {source}")
            continue

        if target.exists() or target.is_symlink():
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)

        if source.is_dir():
            shutil.copytree(source, target, symlinks=False)
        else:
            shutil.copy2(source, target)

        print(f"COPY {source} -> {target}")

