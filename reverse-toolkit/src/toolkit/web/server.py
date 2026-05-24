import json
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from toolkit.project import status as project_status, PROJECTS_ROOT, init_project
from toolkit.analyzer.flow_parser import parse_flows
from toolkit.analyzer.endpoint_extractor import extract_endpoints
from toolkit.analyzer.classifier import classify
from toolkit.analyzer.spec_builder import build_spec
from toolkit.analyzer.doc_generator import generate_doc
from toolkit.generator.scaffold import generate as generate_scaffold
from dataclasses import asdict

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
    proj_status = project_status(app_name)
    if proj_status.get("db_status") == "not_found":
        return templates.TemplateResponse(request, "index.html", {"projects": [], "error": f"项目 {app_name} 不存在"})

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
        "status": proj_status,
        "spec": spec_data,
        "notes": notes,
    })


@app.post("/api/projects")
def create_project(app_name: str = Form(...)):
    init_project(app_name)
    return RedirectResponse(f"/project/{app_name}", status_code=303)


@app.post("/api/projects/{app_name}/analyze")
def run_analyze(app_name: str):
    proj_dir = PROJECTS_ROOT / app_name
    flows_dir = proj_dir / "raw_flows"
    if not flows_dir.exists() or not any(flows_dir.iterdir()):
        return JSONResponse({"ok": False, "error": "没有抓包数据，请先启动代理抓包"}, status_code=400)
    try:
        requests = parse_flows(flows_dir)
        endpoints = extract_endpoints(requests)
        classified = classify(endpoints)
        spec = build_spec(app_name, classified, requests)
        (proj_dir / "api_spec.json").write_text(
            json.dumps(asdict(spec), ensure_ascii=False, indent=2), encoding="utf-8")
        doc = generate_doc(spec)
        (proj_dir / "api_doc.md").write_text(doc, encoding="utf-8")
        return {"ok": True, "endpoints": len(classified), "requests": len(requests)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/projects/{app_name}/scaffold")
def run_scaffold(app_name: str):
    proj_dir = PROJECTS_ROOT / app_name
    spec_path = proj_dir / "api_spec.json"
    if not spec_path.exists():
        return JSONResponse({"ok": False, "error": "没有 api_spec.json，请先分析流量"}, status_code=400)
    try:
        spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
        plugin_code, models_code = generate_scaffold(spec_data)
        (proj_dir / "plugin.py").write_text(plugin_code, encoding="utf-8")
        (proj_dir / "models.py").write_text(models_code, encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/projects/{app_name}/notes")
async def save_notes(app_name: str, request: Request):
    body = await request.json()
    content = body.get("content", "")
    notes_path = PROJECTS_ROOT / app_name / "notes.md"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")
    return {"ok": True}
