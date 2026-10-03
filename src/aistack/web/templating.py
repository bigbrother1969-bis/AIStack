"""
The templates of every screen in AIStack's single web application
(`ADR-0012` § 1), one directory per screen under `templates/`, shipped
inside the package (`pyproject.toml` `[tool.setuptools.package-data]`).
"""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
