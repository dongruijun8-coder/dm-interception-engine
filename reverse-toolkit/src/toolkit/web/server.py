import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from toolkit.project import status as project_status, PROJECTS_ROOT

WEB_DIR = Path(__file__).resolve().parent
app = FastAPI(title="逆向工具箱")

app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = []
    if PROJECTS_ROOT.exists():
        for proj_name in [d.name for d in PROJECTS_ROOT.iterdir() if d.is_dir()]:
            projects.append(project_status(proj_name))
    return templates.TemplateResponse(request, "index.html", {"projects": projects})


@app.get("/project/{app_name}", response_class=HTMLResponse)
def project_detail(request: Request, app_name: str):
    status = project_status(app_name)
    proj_dir = PROJECTS_ROOT / app_name

    spec_data = None
    spec_path = proj_dir / "api_spec.json"
    if spec_path.exists():
        spec_data = json.loads(spec_path.read_text(encoding="utf-8"))

    notes = ""
    notes_path = proj_dir / "notes.md"
    if notes_path.exists():
        notes = notes_path.read_text(encoding="utf-8")

    return templates.TemplateResponse(request, "project.html", {
        "app_name": app_name,
        "status": status,
        "spec": spec_data,
        "notes": notes,
    })
