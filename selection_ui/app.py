from pathlib import Path
import json
import os
import subprocess
import urllib.request
import yaml

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from aistack.catalog.yaml import load_catalog_yaml
from aistack.kernel.bootstrap import create_kernel
from aistack.selection.workflow import build_view, select_from_view
from aistack.selection.yaml import load_selection_yaml, save_selection_yaml
from aistack.providers.repository import RepositoryProvider


REPO_ROOT = Path(__file__).resolve().parents[1]
repository = RepositoryProvider(REPO_ROOT)

# **The first Catalog View consumer** — ADR-0002's ninth step,
# closed 2026-08-29. This screen displayed `catalog.items` and
# built its `Selection` by hand; it now shows a Catalog View
# produced by an engine retrieved from the Kernel, and selects
# through the Selection Engine. GOV-0002/OS-039's surface half.
kernel = create_kernel()

APP_DEF = repository.resolve("selection_ui/definitions/music_android.yml")

app = FastAPI(title="AIStack Selection UI")
templates = Jinja2Templates(
    directory=str(repository.resolve("selection_ui/templates"))
)


def load_app_definition() -> dict:
    return yaml.safe_load(APP_DEF.read_text(encoding="utf-8"))


def get_synced_items(target_root: Path) -> set[str]:
    if not target_root.exists():
        return set()

    return {
        path.name
        for path in target_root.iterdir()
        if path.is_dir() and path.name != ".stfolder"
    }


def get_syncthing_status() -> dict:
    url = os.getenv("SYNCTHING_URL", "http://syncthing:8384").rstrip("/")
    api_key = os.getenv("SYNCTHING_API_KEY")
    folder_id = os.getenv("SYNCTHING_FOLDER_ID", "music-android")

    if not api_key:
        return {
            "available": False,
            "status": "Missing API key",
        }

    try:
        req = urllib.request.Request(
            f"{url}/rest/db/status?folder={folder_id}",
            headers={"X-API-Key": api_key},
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.load(response)

        return {
            "available": True,
            "folder_id": folder_id,
            "state": data.get("state", "unknown"),
            "global_files": data.get("globalFiles"),
            "global_bytes": data.get("globalBytes"),
            "local_files": data.get("localFiles"),
            "local_bytes": data.get("localBytes"),
            "need_files": data.get("needFiles"),
            "need_bytes": data.get("needBytes"),
        }

    except Exception as exc:
        return {
            "available": False,
            "status": str(exc),
        }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    definition = load_app_definition()
    catalog = load_catalog_yaml(repository.resolve(definition["catalog_file"]))
    view = build_view(kernel, catalog, definition["view_id"])
    selection = load_selection_yaml(repository.resolve(definition["selection_file"]))
    selected = set(selection.selected_ids) if selection else set()

    synced = get_synced_items(Path("/media/TechData/Storage/Music-Android"))
    selected_synced = selected & synced
    selected_pending = selected - synced
    synced_not_selected = synced - selected

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "definition": definition,
            "view": view,
            "selected": selected,
            "synced": synced,
            "selected_synced": selected_synced,
            "selected_pending": selected_pending,
            "synced_not_selected": synced_not_selected,
            "selected_synced_percent": round((len(selected_synced) / len(selected) * 100), 1) if selected else 100,
            "catalog_selected_percent": round((len(selected) / len(view.items) * 100), 1) if view.items else 0,
            "status": request.query_params.get("status"),
            "syncthing": get_syncthing_status(),
        },
    )


@app.post("/save")
def save(selected_ids: list[str] = Form(default=[])):
    definition = load_app_definition()
    catalog = load_catalog_yaml(repository.resolve(definition["catalog_file"]))
    view = build_view(kernel, catalog, definition["view_id"])
    selection_path = repository.resolve(definition["selection_file"])

    selection = select_from_view(
        view=view,
        selection_id=definition["app_id"],
        selected_ids=selected_ids,
        metadata={
            "source_catalog": definition["catalog_file"],
            "managed_by": "selection_ui",
        },
    )

    save_selection_yaml(selection, selection_path)

    command = definition.get("generation_command")
    if command:
        subprocess.run(command, cwd=repository.root, check=True)

    return RedirectResponse(
        f"/?status=Selection saved. Generation command executed. {len(selected_ids)} items selected.",
        status_code=303,
    )
