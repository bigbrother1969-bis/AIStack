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

from catalog_engine.yaml_store import load_catalog
from selection_engine.core import Selection
from selection_engine.yaml_store import load_selection, save_selection


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_DEF = REPO_ROOT / "selection_ui" / "definitions" / "music_android.yml"

app = FastAPI(title="AIStack Selection UI")
templates = Jinja2Templates(directory=str(REPO_ROOT / "selection_ui" / "templates"))


def load_app_definition() -> dict:
    return yaml.safe_load(APP_DEF.read_text(encoding="utf-8"))


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
    catalog = load_catalog(REPO_ROOT / definition["catalog_file"])
    selection = load_selection(REPO_ROOT / definition["selection_file"])
    selected = set(selection.selected_ids) if selection else set()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "definition": definition,
            "catalog": catalog,
            "selected": selected,
            "status": request.query_params.get("status"),
            "syncthing": get_syncthing_status(),
        },
    )


@app.post("/save")
def save(selected_ids: list[str] = Form(default=[])):
    definition = load_app_definition()
    catalog = load_catalog(REPO_ROOT / definition["catalog_file"])
    selection_path = REPO_ROOT / definition["selection_file"]

    selection = Selection(
        selection_id=definition["app_id"],
        catalog_id=catalog.catalog_id,
        selected_ids=selected_ids,
        metadata={
            "source_catalog": definition["catalog_file"],
            "managed_by": "selection_ui",
        },
    )

    save_selection(selection, selection_path)

    command = definition.get("generation_command")
    if command:
        subprocess.run(command, cwd=REPO_ROOT, check=True)

    return RedirectResponse(
        f"/?status=Selection saved. Generation command executed. {len(selected_ids)} items selected.",
        status_code=303,
    )
