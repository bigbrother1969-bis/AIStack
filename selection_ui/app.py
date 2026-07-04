from pathlib import Path
import subprocess
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
