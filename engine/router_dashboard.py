"""FastAPI routes for the dashboard."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from engine import db
from engine.plugins import discover_plugins, load_plugin
from engine.pipeline import run_pipeline
from engine.templates import get_templates as get_tpl, set_templates as save_tpl
import asyncio

router = APIRouter(prefix="/api")


class CreateAccountRequest(BaseModel):
    app_name: str
    phone: str = ""
    token: str = ""


class CreateTaskRequest(BaseModel):
    app_name: str
    account_id: int
    config: dict = {}


class TemplatesRequest(BaseModel):
    app_name: str
    templates: list[str]


# ── App/Plugin ──

@router.get("/apps")
async def list_apps():
    plugins = discover_plugins()
    return [{"name": name, "has_plugin": True} for name in plugins]


# ── Account routes ──

@router.get("/accounts")
async def list_accounts(app_name: str = None):
    if app_name:
        return await db.get_accounts_by_app(app_name)
    return []


@router.post("/accounts")
async def create_account(req: CreateAccountRequest):
    account_id = await db.create_account(req.app_name, req.phone, req.token)
    return {"id": account_id}


@router.get("/accounts/{account_id}/health")
async def check_account_health(account_id: int):
    account = await db.get_account(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    plugin = load_plugin(account["app_name"])
    session = account.get("session_data", {})
    health = await plugin.check_health(session)
    await db.update_account_health(account_id, health.value)
    return {"account_id": account_id, "health": health.value}


# ── Task routes ──

@router.get("/tasks")
async def list_tasks(limit: int = 20):
    return await db.list_tasks(limit)


@router.post("/tasks")
async def create_task(req: CreateTaskRequest):
    task_id = await db.create_task(req.account_id, req.app_name, req.config)
    return {"id": task_id}


@router.post("/tasks/{task_id}/run")
async def run_task(task_id: int):
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task["status"] in ("authenticating", "fetching", "sending"):
        raise HTTPException(400, "Task is already running")

    plugin = load_plugin(task["app_name"])
    config = task.get("config", {})

    asyncio.create_task(run_pipeline(plugin, task_id, config))
    return {"task_id": task_id, "status": "started"}


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: int):
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(404)
    stat = await db.get_task_stat(task_id)
    users = await db.get_task_users(task_id)
    return {"task": task, "stat": stat, "user_count": len(users)}


# ── Template routes ──

@router.get("/templates/{app_name}")
async def get_templates_route(app_name: str):
    return {"app_name": app_name, "templates": get_tpl(app_name)}


@router.put("/templates/{app_name}")
async def update_templates(app_name: str, req: TemplatesRequest):
    save_tpl(app_name, req.templates)
    return {"app_name": app_name, "count": len(req.templates)}


# ── Stats ──

@router.get("/stats")
async def get_stats():
    tasks = await db.list_tasks(100)
    apps = discover_plugins()
    total_users = 0
    total_sent = 0
    running = 0
    running_statuses = {"authenticating", "fetching", "sending"}
    for t in tasks:
        total_users += t.get("users_fetched", 0) or 0
        total_sent += t.get("msg_sent", 0) or 0
        if t["status"] in running_statuses:
            running += 1
    return {
        "app_count": len(apps),
        "account_count": 0,
        "total_users": total_users,
        "total_sent": total_sent,
        "running_tasks": running,
    }
