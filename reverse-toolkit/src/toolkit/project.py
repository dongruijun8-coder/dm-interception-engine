from pathlib import Path
from toolkit.db import insert_project, get_project as db_get_project

PROJECTS_ROOT = Path(__file__).resolve().parent.parent.parent / "projects"

def init_project(app_name: str):
    proj_dir = PROJECTS_ROOT / app_name
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "raw_flows").mkdir(exist_ok=True)
    notes = proj_dir / "notes.md"
    if not notes.exists():
        notes.write_text(f"# {app_name} 对抗记录\n\n", encoding="utf-8")
    insert_project(app_name)
    return proj_dir

def get_project_dir(app_name: str) -> Path:
    return PROJECTS_ROOT / app_name

def status(app_name: str) -> dict:
    proj_dir = get_project_dir(app_name)
    if not proj_dir.exists():
        return {"app_name": app_name, "db_status": "not_found", "has_flows": False,
                "has_spec": False, "has_plugin": False, "project_dir": str(proj_dir)}
    has_spec = (proj_dir / "api_spec.json").exists()
    has_plugin = (proj_dir / "plugin.py").exists()
    has_flows = any((proj_dir / "raw_flows").iterdir())
    db_proj = db_get_project(app_name)
    db_status = db_proj["status"] if db_proj else "unknown"
    return {
        "app_name": app_name,
        "db_status": db_status,
        "has_flows": has_flows,
        "has_spec": has_spec,
        "has_plugin": has_plugin,
        "project_dir": str(proj_dir)
    }

def list_all_projects() -> list[str]:
    if not PROJECTS_ROOT.exists():
        return []
    return [d.name for d in PROJECTS_ROOT.iterdir() if d.is_dir()]
