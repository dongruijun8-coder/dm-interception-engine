# 逆向工具箱 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建逆向分析平台化工具链：一键抓包 → 自动分析 → 生成插件骨架，产出 api_spec.json 供运行引擎消费。

**Architecture:** 三个核心模块（proxy → analyzer → generator）通过文件系统串联，共享 schema.py 定义的 api_spec 数据契约。CLI 以 project 为中心，FastAPI Dashboard 提供可视化操作。所有代码在 `reverse-toolkit/src/toolkit/` 下。

**Tech Stack:** Python 3.11+, mitmproxy, Click, Jinja2, FastAPI, uvicorn, SQLite

---

## 文件结构映射

| 文件 | 职责 |
|------|------|
| `src/toolkit/__init__.py` | 空文件，标记包 |
| `src/toolkit/cli.py` | Click CLI 入口，所有子命令 |
| `src/toolkit/schema.py` | ApiSpec 及所有 dataclass 定义 |
| `src/toolkit/project.py` | 项目目录管理 (init/status/list) |
| `src/toolkit/db.py` | SQLite 连接、建表、CRUD |
| `src/toolkit/proxy/__init__.py` | 空 |
| `src/toolkit/proxy/server.py` | mitmproxy 启动 + 过滤配置 |
| `src/toolkit/proxy/addon.py` | mitmproxy addon：域名过滤 + flow 保存 |
| `src/toolkit/analyzer/__init__.py` | 空 |
| `src/toolkit/analyzer/flow_parser.py` | 读取 .mitm 文件，解析为 CapturedRequest list |
| `src/toolkit/analyzer/endpoint_extractor.py` | 去重 + 结构化端点信息 |
| `src/toolkit/analyzer/classifier.py` | 按 URL 规则分类 |
| `src/toolkit/analyzer/spec_builder.py` | 组装 ApiSpec → 写入 api_spec.json |
| `src/toolkit/analyzer/doc_generator.py` | 生成 Markdown API 文档 |
| `src/toolkit/generator/__init__.py` | 空 |
| `src/toolkit/generator/scaffold.py` | 读 api_spec，渲染 Jinja2 模板 |
| `src/toolkit/generator/templates/plugin.py.j2` | 插件骨架模板 |
| `src/toolkit/generator/templates/models.py.j2` | 数据模型模板 |
| `src/toolkit/web/__init__.py` | 空 |
| `src/toolkit/web/server.py` | FastAPI 应用 + 路由 |
| `src/toolkit/web/templates/index.html` | 首页：项目列表 |
| `src/toolkit/web/templates/project.html` | 项目详情页 |
| `src/toolkit/kb/__init__.py` | 空 |
| `src/toolkit/kb/notes.py` | 项目 notes.md 管理 |
| `tests/test_schema.py` | schema 序列化/反序列化测试 |
| `tests/test_project.py` | 项目管理测试 |
| `tests/test_flow_parser.py` | flow 解析测试 |
| `tests/test_endpoint_extractor.py` | 端点提取测试 |
| `tests/test_classifier.py` | 分类器测试 |
| `tests/test_spec_builder.py` | spec 构建测试 |
| `tests/test_scaffold.py` | 骨架生成测试 |
| `requirements.txt` | 项目依赖 |

---

### Task 1: 项目骨架 + 依赖声明

**Files:**
- Create: `reverse-toolkit/requirements.txt`
- Create: `reverse-toolkit/src/toolkit/__init__.py`
- Create: `reverse-toolkit/src/toolkit/proxy/__init__.py`
- Create: `reverse-toolkit/src/toolkit/analyzer/__init__.py`
- Create: `reverse-toolkit/src/toolkit/generator/__init__.py`
- Create: `reverse-toolkit/src/toolkit/web/__init__.py`
- Create: `reverse-toolkit/src/toolkit/kb/__init__.py`
- Create: `reverse-toolkit/tests/__init__.py`
- Create: `reverse-toolkit/projects/.gitkeep`

- [ ] **Step 1: 创建 requirements.txt**

```txt
mitmproxy>=10.0.0
click>=8.0.0
jinja2>=3.0.0
fastapi>=0.100.0
uvicorn>=0.20.0
```

- [ ] **Step 2: 创建所有 `__init__.py` 和目录结构**

```bash
cd reverse-toolkit
mkdir -p src/toolkit/proxy/frida_scripts
mkdir -p src/toolkit/analyzer
mkdir -p src/toolkit/generator/templates
mkdir -p src/toolkit/web/templates
mkdir -p src/toolkit/web/static
mkdir -p src/toolkit/kb
mkdir -p tests
mkdir -p projects
touch src/toolkit/__init__.py
touch src/toolkit/proxy/__init__.py
touch src/toolkit/analyzer/__init__.py
touch src/toolkit/generator/__init__.py
touch src/toolkit/web/__init__.py
touch src/toolkit/kb/__init__.py
touch tests/__init__.py
touch projects/.gitkeep
```

- [ ] **Step 3: 安装依赖验证**

```bash
cd reverse-toolkit && pip install -r requirements.txt
```

Expected: 所有包安装成功，无版本冲突。

- [ ] **Step 4: Commit**

```bash
git add reverse-toolkit/requirements.txt reverse-toolkit/src/ reverse-toolkit/tests/ reverse-toolkit/projects/.gitkeep
git commit -m "chore: scaffold reverse-toolkit project structure and dependencies"
```

---

### Task 2: schema.py — API Spec 共享数据契约

**Files:**
- Create: `reverse-toolkit/src/toolkit/schema.py`
- Create: `reverse-toolkit/tests/test_schema.py`

- [ ] **Step 1: 编写失败的序列化测试**

`reverse-toolkit/tests/test_schema.py`:

```python
import json
from dataclasses import asdict
from toolkit.schema import (
    ApiSpec, AuthInfo, LoginStep, CommonParams,
    EndpointDef, PreStep, AntiReverseInfo
)

def test_api_spec_roundtrip():
    """ApiSpec 可以序列化为 JSON 并反序列化回来"""
    spec = ApiSpec(
        app="popo",
        version="1.7.40",
        base_url="https://api.pp.weimipopo.com",
        auth=AuthInfo(
            type="token",
            login_flow=[
                LoginStep(order=1, endpoint="/sms", method="POST",
                          params={"phone": "string"}, extract="smsCode"),
                LoginStep(order=2, endpoint="/login", method="POST",
                          params={"phone": "string", "smsCode": "string"}, extract=None),
            ]
        ),
        common_params=CommonParams(
            headers={"User-Agent": "okhttp/3.14.9"},
            body=["app", "build", "channel", "meid", "token", "uid", "version"],
            url_params=[]
        ),
        endpoints=[
            EndpointDef(
                name="room_list",
                method="POST",
                path="/plpl/room/main/listByCat",
                category="rooms",
                params={"catId": 1, "limit": 20, "offset": 0},
                pagination="offset_limit",
                response_model="rooms[]",
                pre_steps=None
            ),
            EndpointDef(
                name="send_message",
                method="POST",
                path="/plpl/relation/in/chat/send",
                category="message",
                params={},
                pagination=None,
                response_model=None,
                pre_steps=[
                    PreStep(endpoint="/plpl/relation/get/user/in/chat", extract="tid", pass_to="tid"),
                    PreStep(endpoint="/plpl/pr/chat/preCheck", extract="msgChatId", pass_to="msgChatId"),
                ]
            ),
        ],
        status_codes={"S_OK": "成功", "F_BAN": "封禁"},
        anti_reverse=AntiReverseInfo(
            ssl_pinning=True,
            encryption="AES/CBC/PKCS5 (手机号字段)",
            device_fingerprint="MEID + IMEI",
            captcha="网易易盾",
            notes="richLevel < 6 无法私信"
        )
    )
    # 序列化
    d = asdict(spec)
    json_str = json.dumps(d, ensure_ascii=False, indent=2)
    # 反序列化
    loaded = json.loads(json_str)
    assert loaded["app"] == "popo"
    assert loaded["auth"]["type"] == "token"
    assert len(loaded["auth"]["login_flow"]) == 2
    assert loaded["auth"]["login_flow"][0]["extract"] == "smsCode"
    assert loaded["auth"]["login_flow"][1]["extract"] is None
    assert len(loaded["endpoints"]) == 2
    assert loaded["endpoints"][0]["category"] == "rooms"
    assert loaded["endpoints"][1]["pre_steps"][0]["extract"] == "tid"
    assert loaded["status_codes"]["S_OK"] == "成功"
    assert loaded["anti_reverse"]["ssl_pinning"] is True
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd reverse-toolkit && python -m pytest tests/test_schema.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'toolkit.schema'`

需要设置 PYTHONPATH:

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_schema.py -v
```

Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现 schema.py**

`reverse-toolkit/src/toolkit/schema.py`:

```python
from dataclasses import dataclass, field


@dataclass
class LoginStep:
    order: int
    endpoint: str
    method: str = "POST"
    params: dict = field(default_factory=dict)
    extract: str | None = None


@dataclass
class AuthInfo:
    type: str  # "token" | "cookie" | "oauth" | "none"
    login_flow: list[LoginStep] = field(default_factory=list)


@dataclass
class CommonParams:
    headers: dict[str, str] = field(default_factory=dict)
    body: list[str] = field(default_factory=list)
    url_params: list[str] = field(default_factory=list)


@dataclass
class PreStep:
    endpoint: str
    extract: str
    pass_to: str


@dataclass
class EndpointDef:
    name: str
    method: str
    path: str
    category: str  # auth|rooms|rank|message|profile|other
    params: dict = field(default_factory=dict)
    pagination: str | None = None  # offset_limit|page_num|cursor|None
    response_model: str | None = None
    pre_steps: list[PreStep] | None = None


@dataclass
class AntiReverseInfo:
    ssl_pinning: bool = False
    encryption: str = "none"
    device_fingerprint: str = "none"
    captcha: str = "none"
    notes: str = ""


@dataclass
class ApiSpec:
    app: str
    version: str
    base_url: str
    auth: AuthInfo = field(default_factory=AuthInfo)
    common_params: CommonParams = field(default_factory=CommonParams)
    endpoints: list[EndpointDef] = field(default_factory=list)
    status_codes: dict[str, str] = field(default_factory=dict)
    anti_reverse: AntiReverseInfo = field(default_factory=AntiReverseInfo)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_schema.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reverse-toolkit/src/toolkit/schema.py reverse-toolkit/tests/test_schema.py
git commit -m "feat: add ApiSpec schema dataclasses with serialization"
```

---

### Task 3: db.py — SQLite 数据库层

**Files:**
- Create: `reverse-toolkit/src/toolkit/db.py`

- [ ] **Step 1: 实现 db.py**

`reverse-toolkit/src/toolkit/db.py`:

```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "toolkit.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL UNIQUE,
            version TEXT,
            base_url TEXT,
            status TEXT DEFAULT 'created',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS endpoint_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            host TEXT NOT NULL,
            category TEXT,
            first_seen_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(app_name, method, path)
        );

        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()

def insert_project(app_name: str, version: str = "", base_url: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO project (app_name, version, base_url, status, updated_at) "
        "VALUES (?, ?, ?, 'created', datetime('now','localtime'))",
        (app_name, version, base_url)
    )
    conn.commit()
    conn.close()

def update_project_status(app_name: str, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE project SET status=?, updated_at=datetime('now','localtime') WHERE app_name=?",
        (status, app_name)
    )
    conn.commit()
    conn.close()

def list_projects() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM project ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project(app_name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM project WHERE app_name=?", (app_name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def insert_scan_log(app_name: str, action: str, detail: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO scan_log (app_name, action, detail) VALUES (?, ?, ?)",
        (app_name, action, detail)
    )
    conn.commit()
    conn.close()
```

- [ ] **Step 2: 交互验证**

```bash
cd reverse-toolkit && PYTHONPATH=src python -c "
from toolkit.db import init_db, insert_project, list_projects
init_db()
insert_project('popo', '1.7.40', 'https://api.pp.weimipopo.com')
print(list_projects())
"
```

Expected: 输出包含 `{'app_name': 'popo', 'version': '1.7.40', ...}` 的列表

- [ ] **Step 3: Commit**

```bash
git add reverse-toolkit/src/toolkit/db.py
git commit -m "feat: add SQLite database layer for project metadata"
```

---

### Task 4: project.py — 项目管理逻辑

**Files:**
- Create: `reverse-toolkit/src/toolkit/project.py`
- Create: `reverse-toolkit/tests/test_project.py`

- [ ] **Step 1: 编写测试**

`reverse-toolkit/tests/test_project.py`:

```python
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from toolkit.project import (
    init_project, get_project_dir, PROJECTS_ROOT
)

def test_init_project_creates_directories():
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp)
        with patch('toolkit.project.PROJECTS_ROOT', projects_root):
            init_project("testapp")
            proj_dir = projects_root / "testapp"
            assert proj_dir.is_dir()
            assert (proj_dir / "raw_flows").is_dir()
            assert (proj_dir / "notes.md").is_file()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_project.py -v
```

Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现 project.py**

`reverse-toolkit/src/toolkit/project.py`:

```python
from pathlib import Path
from toolkit.db import insert_project, list_projects, get_project as db_get_project

PROJECTS_ROOT = Path(__file__).resolve().parent.parent / "projects"

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

def status(app_name: str) -> str:
    proj_dir = get_project_dir(app_name)
    if not proj_dir.exists():
        return "not_found"
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_project.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reverse-toolkit/src/toolkit/project.py reverse-toolkit/tests/test_project.py
git commit -m "feat: add project management with init/status/list"
```

---

### Task 5: cli.py — CLI 入口骨架

**Files:**
- Create: `reverse-toolkit/src/toolkit/cli.py`

- [ ] **Step 1: 实现 CLI 入口**

`reverse-toolkit/src/toolkit/cli.py`:

```python
import click
from toolkit.db import init_db

@click.group()
def main():
    """逆向工具箱 — 一键抓包 → 自动分析 → 生成插件骨架"""
    init_db()

@main.command()
@click.option("--app", required=True, help="APP 名称")
def init(app):
    """创建新项目"""
    from toolkit.project import init_project
    p = init_project(app)
    click.echo(f"项目已创建: {p}")

@main.command()
@click.option("--app", required=True, help="APP 名称")
def status_cmd(app):
    """查看项目状态"""
    from toolkit.project import status
    s = status(app)
    click.echo(f"APP: {s['app_name']}")
    click.echo(f"状态: {s['db_status']}")
    click.echo(f"抓包: {'有' if s['has_flows'] else '无'}")
    click.echo(f"api_spec: {'有' if s['has_spec'] else '无'}")
    click.echo(f"插件: {'有' if s['has_plugin'] else '无'}")

@main.command()
@click.option("--app", required=True, help="APP 名称")
def analyze(app):
    """分析流量生成 api_spec.json"""
    from toolkit.analyzer.flow_parser import parse_flows
    from toolkit.analyzer.endpoint_extractor import extract_endpoints
    from toolkit.analyzer.classifier import classify
    from toolkit.analyzer.spec_builder import build_spec
    from toolkit.analyzer.doc_generator import generate_doc
    from toolkit.project import get_project_dir

    proj = get_project_dir(app)
    flows_dir = proj / "raw_flows"
    if not flows_dir.exists() or not any(flows_dir.iterdir()):
        click.echo(f"错误: {app} 没有抓包数据，请先运行 proxy start")
        return

    requests = parse_flows(flows_dir)
    click.echo(f"解析到 {len(requests)} 条请求")

    endpoints = extract_endpoints(requests)
    click.echo(f"提取到 {len(endpoints)} 个唯一端点")

    classified = classify(endpoints)
    spec = build_spec(app, classified, requests)
    spec_path = proj / "api_spec.json"
    import json
    from dataclasses import asdict
    spec_path.write_text(json.dumps(asdict(spec), ensure_ascii=False, indent=2), encoding="utf-8")
    click.echo(f"api_spec 已保存: {spec_path}")

    doc = generate_doc(spec)
    doc_path = proj / "api_doc.md"
    doc_path.write_text(doc, encoding="utf-8")
    click.echo(f"API 文档已保存: {doc_path}")

@main.command()
@click.option("--app", required=True, help="APP 名称")
def scaffold(app):
    """生成插件骨架代码"""
    from toolkit.generator.scaffold import generate
    from toolkit.project import get_project_dir

    proj = get_project_dir(app)
    spec_path = proj / "api_spec.json"
    if not spec_path.exists():
        click.echo(f"错误: {app} 没有 api_spec.json，请先运行 analyze")
        return

    import json
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    plugin_code, models_code = generate(spec_data)
    (proj / "plugin.py").write_text(plugin_code, encoding="utf-8")
    (proj / "models.py").write_text(models_code, encoding="utf-8")
    click.echo(f"插件骨架已生成: {proj / 'plugin.py'}")
    click.echo(f"数据模型已生成: {proj / 'models.py'}")

@main.command()
@click.option("--app", required=True, help="APP 名称")
@click.option("--host", required=True, help="目标域名，如 *.weimipopo.com")
@click.option("--frida", default=None, help="Frida 脚本路径")
def proxy_start(app, host, frida):
    """启动代理抓包"""
    from toolkit.proxy.server import start_proxy
    from toolkit.project import get_project_dir
    proj = get_project_dir(app)
    start_proxy(app=app, host_filter=host, output_dir=str(proj / "raw_flows"), frida_script=frida)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 CLI 可加载**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m toolkit.cli --help
```

Expected: 显示帮助信息（analyze、scaffold、init 等命令可能因依赖模块未实现而报 import error，但 `--help` 应能显示 Click group 的基本输出）。

> **注意：** 此时 `analyze`、`scaffold`、`proxy_start` 命令引用的模块尚未实现，因此单独运行这些子命令会报 import error。这符合预期 —— 我们在接下来的 Task 中逐一实现。

- [ ] **Step 3: Commit**

```bash
git add reverse-toolkit/src/toolkit/cli.py
git commit -m "feat: add CLI entry point with command stubs"
```

---

### Task 6: analyzer/flow_parser.py — mitmproxy 流量解析

**Files:**
- Create: `reverse-toolkit/src/toolkit/analyzer/flow_parser.py`
- Create: `reverse-toolkit/tests/test_flow_parser.py`

- [ ] **Step 1: 编写测试（使用真实 mitmproxy dump 文件）**

`reverse-toolkit/tests/test_flow_parser.py`:

```python
from pathlib import Path
from toolkit.analyzer.flow_parser import parse_flows, CapturedRequest

def test_parse_flows_from_dir(tmp_path):
    """解析目录中的 .mitm 文件"""
    dump_dir = tmp_path / "raw_flows" / "2026-05-19"
    dump_dir.mkdir(parents=True)

    # 创建一个最简单的 mitmproxy flow 文件（用 tflow 格式）
    # mitmproxy dump 格式是标准 mitmproxy flow dump
    # 这里用一段实际的 json 格式 flow 来做测试
    sample_flow = {
        "request": {
            "method": "POST",
            "path": b"/plpl/room/main/listByCat",
            "host": "api.pp.weimipopo.com",
            "headers": {"Content-Type": "application/json"},
            "content": b'{"catId":1,"limit":20}',
            "timestamp_start": 1716100000.0
        },
        "response": {
            "status_code": 200,
            "content": b'{"data":{"rooms":[]}}',
            "headers": {"Content-Type": "application/json"}
        }
    }
    import json
    (dump_dir / "flows.mitm").write_text(json.dumps([sample_flow]), encoding="utf-8")

    requests = parse_flows(dump_dir)
    assert len(requests) >= 1
    req = requests[0]
    assert req.method == "POST"
    assert req.host == "api.pp.weimipopo.com"
    assert "/plpl/room" in req.path
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_flow_parser.py -v
```

Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现 flow_parser.py**

`reverse-toolkit/src/toolkit/analyzer/flow_parser.py`:

```python
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class CapturedRequest:
    method: str
    path: str
    host: str
    req_headers: dict
    req_body: str
    resp_status: int
    resp_body: str
    content_type: str
    timestamp: float


def parse_flows(flows_dir: Path) -> list[CapturedRequest]:
    results = []
    for f in flows_dir.rglob("*.mitm"):
        try:
            text = f.read_text(encoding="utf-8")
            flows = json.loads(text)
            if isinstance(flows, list):
                for flow in flows:
                    req = flow.get("request", {})
                    resp = flow.get("response", {})
                    req_headers = req.get("headers", {})
                    content = req.get("content", b"")
                    if isinstance(content, bytes):
                        content = content.decode("utf-8", errors="replace")
                    resp_content = resp.get("content", b"")
                    if isinstance(resp_content, bytes):
                        resp_content = resp_content.decode("utf-8", errors="replace")
                    results.append(CapturedRequest(
                        method=req.get("method", "GET"),
                        path=req.get("path", ""),
                        host=req.get("host", ""),
                        req_headers=req_headers,
                        req_body=content,
                        resp_status=resp.get("status_code", 0),
                        resp_body=resp_content,
                        content_type=req_headers.get("Content-Type", ""),
                        timestamp=req.get("timestamp_start", 0.0)
                    ))
        except Exception:
            continue
    return results
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_flow_parser.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reverse-toolkit/src/toolkit/analyzer/flow_parser.py reverse-toolkit/tests/test_flow_parser.py
git commit -m "feat: add mitmproxy flow parser"
```

---

### Task 7: analyzer/endpoint_extractor.py — API 端点提取与去重

**Files:**
- Create: `reverse-toolkit/src/toolkit/analyzer/endpoint_extractor.py`
- Create: `reverse-toolkit/tests/test_endpoint_extractor.py`

- [ ] **Step 1: 编写测试**

`reverse-toolkit/tests/test_endpoint_extractor.py`:

```python
from toolkit.analyzer.endpoint_extractor import extract_endpoints, ExtractedEndpoint
from toolkit.analyzer.flow_parser import CapturedRequest

def make_req(method="POST", path="/api/test", host="api.example.com",
             req_body='{"a":1}', resp_body='{"data":[]}', resp_status=200):
    return CapturedRequest(
        method=method, path=path, host=host,
        req_headers={}, req_body=req_body,
        resp_status=resp_status, resp_body=resp_body,
        content_type="application/json", timestamp=0.0
    )

def test_dedup_same_path():
    reqs = [
        make_req(path="/api/rooms/list"),
        make_req(path="/api/rooms/list"),
        make_req(path="/api/rooms/list"),
    ]
    eps = extract_endpoints(reqs)
    assert len(eps) == 1
    assert eps[0].method == "POST"
    assert eps[0].path == "/api/rooms/list"

def test_preserves_params_from_first_seen():
    reqs = [
        make_req(path="/api/search", req_body='{"q":"hello","limit":20}'),
        make_req(path="/api/search", req_body='{"q":"world","limit":50}'),
    ]
    eps = extract_endpoints(reqs)
    assert len(eps) == 1
    assert "q" in eps[0].sample_params

def test_sorts_by_path():
    reqs = [
        make_req(path="/zzz"),
        make_req(path="/aaa"),
        make_req(path="/mmm"),
    ]
    eps = extract_endpoints(reqs)
    paths = [e.path for e in eps]
    assert paths == sorted(paths)

def test_ignores_static_resources():
    reqs = [
        make_req(path="/api/users", content_type="application/json"),
        make_req(path="/favicon.ico", content_type="image/x-icon"),
        make_req(path="/static/app.js", content_type="application/javascript"),
        make_req(path="/styles/main.css", content_type="text/css"),
    ]
    eps = extract_endpoints(reqs)
    paths = [e.path for e in eps]
    assert "/favicon.ico" not in paths
    assert "/static/app.js" not in paths
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_endpoint_extractor.py -v
```

Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现 endpoint_extractor.py**

`reverse-toolkit/src/toolkit/analyzer/endpoint_extractor.py`:

```python
from dataclasses import dataclass, field
from toolkit.analyzer.flow_parser import CapturedRequest
import json

STATIC_EXTENSIONS = {".js", ".css", ".png", ".jpg", ".gif", ".svg", ".ico",
                     ".woff", ".woff2", ".ttf", ".map", ".webp", ".mp4"}


@dataclass
class ExtractedEndpoint:
    method: str
    path: str
    host: str
    content_type: str
    sample_params: dict = field(default_factory=dict)
    sample_response: str = ""
    hit_count: int = 1


def extract_endpoints(requests: list[CapturedRequest]) -> list[ExtractedEndpoint]:
    seen: dict[str, ExtractedEndpoint] = {}

    for req in requests:
        if _is_static(req.path, req.content_type):
            continue

        key = f"{req.method}:{req.host}:{req.path}"
        if key in seen:
            seen[key].hit_count += 1
            continue

        params = _extract_params(req.req_body, req.content_type)
        ep = ExtractedEndpoint(
            method=req.method,
            path=req.path,
            host=req.host,
            content_type=req.content_type,
            sample_params=params,
            sample_response=req.resp_body[:500],
        )
        seen[key] = ep

    return sorted(seen.values(), key=lambda e: e.path)


def _is_static(path: str, content_type: str) -> bool:
    for ext in STATIC_EXTENSIONS:
        if path.lower().endswith(ext):
            return True
    static_cts = ["image/", "text/css", "font/", "video/", "audio/"]
    for ct in static_cts:
        if content_type.startswith(ct):
            return True
    return False


def _extract_params(body: str, content_type: str) -> dict:
    if not body:
        return {}
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            return {k: type(v).__name__ for k, v in data.items()}
    except (json.JSONDecodeError, ValueError):
        pass
    return {}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_endpoint_extractor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reverse-toolkit/src/toolkit/analyzer/endpoint_extractor.py reverse-toolkit/tests/test_endpoint_extractor.py
git commit -m "feat: add endpoint extractor with dedup and static resource filter"
```

---

### Task 8: analyzer/classifier.py — API 分类引擎

**Files:**
- Create: `reverse-toolkit/src/toolkit/analyzer/classifier.py`
- Create: `reverse-toolkit/tests/test_classifier.py`

- [ ] **Step 1: 编写测试**

`reverse-toolkit/tests/test_classifier.py`:

```python
from toolkit.analyzer.classifier import classify, CATEGORY_RULES
from toolkit.analyzer.endpoint_extractor import ExtractedEndpoint

def make_ep(path, method="POST", host="api.example.com"):
    return ExtractedEndpoint(
        method=method, path=path, host=host,
        content_type="application/json"
    )

def test_classify_auth():
    eps = [make_ep("/api/v1/login"), make_ep("/api/v1/register"), make_ep("/sms/send")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "auth"

def test_classify_rooms():
    eps = [make_ep("/room/list"), make_ep("/live/hot"), make_ep("/category/live")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "rooms"

def test_classify_rank():
    eps = [make_ep("/rank/weekly"), make_ep("/contribute/list"), make_ep("/leaderboard/top")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "rank"

def test_classify_message():
    eps = [make_ep("/chat/send"), make_ep("/message/inbox"), make_ep("/im/thread")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "message"

def test_classify_profile():
    eps = [make_ep("/user/profile"), make_ep("/user/info"), make_ep("/card/detail")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "profile"

def test_classify_other_fallback():
    eps = [make_ep("/config/get"), make_ep("/health/check")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "other"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_classifier.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 classifier.py**

`reverse-toolkit/src/toolkit/analyzer/classifier.py`:

```python
from toolkit.analyzer.endpoint_extractor import ExtractedEndpoint

CATEGORY_RULES = {
    "auth":     ["/login", "/register", "/sms", "/token", "/auth", "/signin", "/signup"],
    "rooms":    ["/list", "/hot", "/category", "/room", "/live", "/search"],
    "rank":     ["/rank", "/contribute", "/leaderboard", "/top", "/gift"],
    "message":  ["/chat", "/send", "/message", "/inbox", "/im", "/conversation"],
    "profile":  ["/user", "/profile", "/info", "/card", "/account"],
}


def classify(endpoints: list[ExtractedEndpoint]) -> list[dict]:
    result = []
    for ep in endpoints:
        category = _classify_one(ep.path.lower(), ep.method.lower(), ep.host.lower())
        result.append({
            "method": ep.method,
            "path": ep.path,
            "host": ep.host,
            "category": category,
            "content_type": ep.content_type,
            "sample_params": ep.sample_params,
            "sample_response": ep.sample_response,
            "hit_count": ep.hit_count,
        })
    return result


def _classify_one(path: str, method: str, host: str) -> str:
    for cat, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in path:
                return cat
    return "other"
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_classifier.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reverse-toolkit/src/toolkit/analyzer/classifier.py reverse-toolkit/tests/test_classifier.py
git commit -m "feat: add API endpoint classifier with keyword rules"
```

---

### Task 9: analyzer/spec_builder.py — 组装 ApiSpec

**Files:**
- Create: `reverse-toolkit/src/toolkit/analyzer/spec_builder.py`
- Create: `reverse-toolkit/tests/test_spec_builder.py`

- [ ] **Step 1: 编写测试**

`reverse-toolkit/tests/test_spec_builder.py`:

```python
from toolkit.analyzer.spec_builder import build_spec, detect_common_params, detect_status_codes
from toolkit.analyzer.flow_parser import CapturedRequest
from toolkit.analyzer.endpoint_extractor import extract_endpoints
from toolkit.analyzer.classifier import classify

def test_build_spec_structure():
    reqs = [
        CapturedRequest(method="POST", path="/api/login", host="api.example.com",
                        req_headers={"Authorization": "Bearer xxx"},
                        req_body='{"phone":"13800138000","token":"abc"}',
                        resp_status=200, resp_body='{"status":"S_OK"}',
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/room/list", host="api.example.com",
                        req_headers={"Authorization": "Bearer xxx"},
                        req_body='{"catId":1,"token":"abc","limit":20}',
                        resp_status=200, resp_body='{"status":"S_OK","data":[]}',
                        content_type="application/json", timestamp=0.0),
    ]
    eps = extract_endpoints(reqs)
    classified = classify(eps)
    spec = build_spec("testapp", classified, reqs)
    assert spec.app == "testapp"
    assert spec.base_url == "https://api.example.com"
    assert len(spec.endpoints) == 2
    assert spec.status_codes == {"S_OK": ""}

def test_detect_common_params():
    reqs = [
        CapturedRequest(method="POST", path="/api/a", host="api.example.com",
                        req_headers={}, req_body='{"a":1,"b":2,"c":3}',
                        resp_status=200, resp_body="{}",
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/b", host="api.example.com",
                        req_headers={}, req_body='{"a":10,"b":20,"d":40}',
                        resp_status=200, resp_body="{}",
                        content_type="application/json", timestamp=0.0),
    ]
    common = detect_common_params(reqs)
    assert "a" in common
    assert "b" in common
    assert "c" not in common  # 只在第一个请求中出现

def test_detect_status_codes():
    reqs = [
        CapturedRequest(method="POST", path="/api/a", host="api.example.com",
                        req_headers={}, req_body="{}",
                        resp_status=200, resp_body='{"status":"S_OK"}',
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/b", host="api.example.com",
                        req_headers={}, req_body="{}",
                        resp_status=200, resp_body='{"status":"F_BAN"}',
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/c", host="api.example.com",
                        req_headers={}, req_body="{}",
                        resp_status=200, resp_body='{"status":"F_BAN"}',
                        content_type="application/json", timestamp=0.0),
    ]
    codes = detect_status_codes(reqs)
    assert "S_OK" in codes
    assert "F_BAN" in codes
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_spec_builder.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 spec_builder.py**

`reverse-toolkit/src/toolkit/analyzer/spec_builder.py`:

```python
import json
from toolkit.schema import ApiSpec, AuthInfo, CommonParams, EndpointDef, AntiReverseInfo
from toolkit.analyzer.flow_parser import CapturedRequest


def build_spec(app: str, classified_endpoints: list[dict], requests: list[CapturedRequest]) -> ApiSpec:
    host = requests[0].host if requests else ""
    base_url = f"https://{host}"

    common_body = list(detect_common_params(requests))
    common_headers = detect_common_headers(requests)

    status_codes = detect_status_codes(requests)

    endpoints = []
    for ep in classified_endpoints:
        endpoints.append(EndpointDef(
            name=_derive_name(ep["path"]),
            method=ep["method"],
            path=ep["path"],
            category=ep["category"],
            params=ep["sample_params"],
            pagination=_detect_pagination(ep),
            response_model=None,
            pre_steps=None
        ))

    return ApiSpec(
        app=app,
        version="",
        base_url=base_url,
        auth=AuthInfo(type="token"),
        common_params=CommonParams(headers=common_headers, body=common_body),
        endpoints=endpoints,
        status_codes=status_codes,
        anti_reverse=AntiReverseInfo()
    )


def detect_common_params(requests: list[CapturedRequest]) -> set[str]:
    if not requests:
        return set()
    parsed_bodies = []
    for r in requests:
        try:
            d = json.loads(r.req_body)
            if isinstance(d, dict):
                parsed_bodies.append(d)
        except (json.JSONDecodeError, ValueError):
            continue
    if not parsed_bodies:
        return set()
    # 在超过半数的请求中出现的 key 视为公共参数
    threshold = max(1, len(parsed_bodies) // 2)
    all_keys = set()
    for body in parsed_bodies:
        all_keys.update(body.keys())
    common = set()
    for key in all_keys:
        count = sum(1 for b in parsed_bodies if key in b)
        if count >= threshold:
            common.add(key)
    return common


def detect_common_headers(requests: list[CapturedRequest]) -> dict[str, str]:
    if not requests:
        return {}
    # 取第一个有意义的请求的 headers
    for r in requests:
        h = r.req_headers
        if h:
            return {k: v for k, v in h.items()
                    if k.lower() not in ("host", "content-length", "content-type", "accept-encoding")}
    return {}


def detect_status_codes(requests: list[CapturedRequest]) -> dict[str, str]:
    codes: dict[str, int] = {}
    for r in requests:
        try:
            d = json.loads(r.resp_body)
            if isinstance(d, dict) and "status" in d:
                s = d["status"]
                codes[s] = codes.get(s, 0) + 1
        except (json.JSONDecodeError, ValueError):
            continue
    return {k: "" for k in codes if codes[k] >= 1}


def _derive_name(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.isdigit()]
    if len(parts) >= 2:
        return "_".join(parts[-2:])
    return parts[-1] if parts else "unknown"


def _detect_pagination(ep: dict) -> str | None:
    params = ep.get("sample_params", {})
    param_keys = set(params.keys())
    if {"offset", "limit"}.issubset(param_keys):
        return "offset_limit"
    if {"page", "pageSize"}.issubset(param_keys) or {"pageNum", "pageSize"}.issubset(param_keys):
        return "page_num"
    if "cursor" in param_keys:
        return "cursor"
    return None
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_spec_builder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add reverse-toolkit/src/toolkit/analyzer/spec_builder.py reverse-toolkit/tests/test_spec_builder.py
git commit -m "feat: add spec builder that assembles ApiSpec from classified endpoints"
```

---

### Task 10: analyzer/doc_generator.py — Markdown 文档生成

**Files:**
- Create: `reverse-toolkit/src/toolkit/analyzer/doc_generator.py`

- [ ] **Step 1: 实现 doc_generator.py**

`reverse-toolkit/src/toolkit/analyzer/doc_generator.py`:

```python
from toolkit.schema import ApiSpec


def generate_doc(spec: ApiSpec) -> str:
    lines = []
    lines.append(f"# {spec.app} API 分析报告")
    lines.append("")
    lines.append(f"**Base URL:** {spec.base_url}")
    lines.append(f"**版本:** {spec.version}")
    lines.append(f"**认证方式:** {spec.auth.type}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 公共参数")
    lines.append("")
    if spec.common_params.headers:
        lines.append("### 公共请求头")
        lines.append("```")
        for k, v in spec.common_params.headers.items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        lines.append("")
    if spec.common_params.body:
        lines.append("### 公共 Body 字段")
        lines.append("")
        for field in spec.common_params.body:
            lines.append(f"- `{field}`")
        lines.append("")

    lines.append("## 状态码")
    lines.append("")
    if spec.status_codes:
        lines.append("| 状态码 | 说明 |")
        lines.append("|--------|------|")
        for code, desc in spec.status_codes.items():
            lines.append(f"| `{code}` | {desc} |")
    lines.append("")

    lines.append("## API 端点")
    lines.append("")

    categories: dict[str, list] = {}
    for ep in spec.endpoints:
        cat = ep.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ep)

    for cat in ["auth", "rooms", "rank", "message", "profile", "other"]:
        if cat not in categories:
            continue
        lines.append(f"### {_cat_label(cat)}")
        lines.append("")
        lines.append("| 方法 | 路径 | 分页 | 参数 |")
        lines.append("|------|------|------|------|")
        for ep in categories[cat]:
            params_str = ", ".join(ep.params.keys()) if ep.params else "-"
            pagination = ep.pagination or "-"
            lines.append(f"| {ep.method} | `{ep.path}` | {pagination} | {params_str} |")
        lines.append("")

    lines.append("## 反调信息")
    lines.append("")
    ar = spec.anti_reverse
    lines.append(f"- SSL Pinning: {'是' if ar.ssl_pinning else '否'}")
    lines.append(f"- 加密: {ar.encryption}")
    lines.append(f"- 设备指纹: {ar.device_fingerprint}")
    lines.append(f"- 验证码: {ar.captcha}")
    if ar.notes:
        lines.append(f"- 备注: {ar.notes}")
    lines.append("")

    return "\n".join(lines)


def _cat_label(cat: str) -> str:
    return {
        "auth": "认证",
        "rooms": "房间",
        "rank": "排行榜",
        "message": "私信",
        "profile": "用户",
        "other": "其他"
    }.get(cat, cat)
```

- [ ] **Step 2: 快速验证**

```bash
cd reverse-toolkit && PYTHONPATH=src python -c "
from toolkit.schema import ApiSpec, EndpointDef, CommonParams, AuthInfo, AntiReverseInfo
from toolkit.analyzer.doc_generator import generate_doc

spec = ApiSpec(
    app='demo', version='1.0', base_url='https://api.example.com',
    auth=AuthInfo(type='token'),
    common_params=CommonParams(body=['token', 'uid']),
    endpoints=[EndpointDef(name='login', method='POST', path='/login', category='auth')],
    status_codes={'S_OK': '成功'},
    anti_reverse=AntiReverseInfo()
)
doc = generate_doc(spec)
assert '# demo API' in doc
assert 'token' in doc
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add reverse-toolkit/src/toolkit/analyzer/doc_generator.py
git commit -m "feat: add Markdown API doc generator"
```

---

### Task 11: generator — Jinja2 模板 + scaffold

**Files:**
- Create: `reverse-toolkit/src/toolkit/generator/templates/plugin.py.j2`
- Create: `reverse-toolkit/src/toolkit/generator/templates/models.py.j2`
- Create: `reverse-toolkit/src/toolkit/generator/scaffold.py`
- Create: `reverse-toolkit/tests/test_scaffold.py`

- [ ] **Step 1: 编写测试**

`reverse-toolkit/tests/test_scaffold.py`:

```python
from toolkit.generator.scaffold import generate

def test_generate_plugin_and_models():
    spec = {
        "app": "popo",
        "base_url": "https://api.pp.weimipopo.com",
        "auth": {"type": "token", "login_flow": [
            {"order": 1, "endpoint": "/sms", "method": "POST", "params": {"phone": "string"}, "extract": None}
        ]},
        "endpoints": [
            {"name": "room_list", "method": "POST", "path": "/room/list",
             "category": "rooms", "params": {"catId": "int"},
             "pagination": "offset_limit", "response_model": "rooms[]", "pre_steps": None},
            {"name": "send_message", "method": "POST", "path": "/chat/send",
             "category": "message", "params": {},
             "pagination": None, "response_model": None,
             "pre_steps": [{"endpoint": "/chat/pre", "extract": "tid", "pass_to": "tid"}]},
        ],
        "status_codes": {"S_OK": ""},
        "anti_reverse": {"ssl_pinning": False, "encryption": "none",
                         "device_fingerprint": "none", "captcha": "none", "notes": ""}
    }
    plugin_code, models_code = generate(spec)

    # plugin.py 必须包含的内容
    assert "class PopoPlugin" in plugin_code
    assert "def authenticate" in plugin_code
    assert "def fetch_rooms" in plugin_code
    assert "def fetch_users" in plugin_code
    assert "def send_message" in plugin_code
    assert "def check_account_health" in plugin_code
    assert "BasePlugin" in plugin_code
    assert "https://api.pp.weimipopo.com" in plugin_code

    # models.py 必须包含的内容
    assert "class Room" in models_code or "Room" in models_code
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_scaffold.py -v
```

Expected: FAIL

- [ ] **Step 3: 编写 plugin.py.j2 模板**

`reverse-toolkit/src/toolkit/generator/templates/plugin.py.j2`:

```jinja2
from engine import BasePlugin, AuthResult, Room, User, SendResult, HealthStatus

class {{ app|capitalize }}Plugin(BasePlugin):
    APP_NAME = "{{ app }}"
    BASE_URL = "{{ base_url }}"

    def authenticate(self, credential: dict) -> AuthResult:
        # TODO: 实现认证逻辑
{% if auth.login_flow %}
{% for step in auth.login_flow %}
        # Step {{ step.order }}: {{ step.method }} {{ step.endpoint }}
{% endfor %}
{% endif %}
        # credential 包含: {{ credential_hint }}
        pass

    def fetch_rooms(self, filters: dict) -> list[Room]:
{% for ep in endpoints if ep.category == "rooms" %}
        # {{ ep.method }} {{ ep.path }}
        # 参数: {{ ep.params }}
{% if ep.pagination %}
        # 分页: {{ ep.pagination }}
{% endif %}
{% endfor %}
        pass

    def fetch_users(self, room: Room) -> list[User]:
{% for ep in endpoints if ep.category == "rank" %}
        # {{ ep.method }} {{ ep.path }}
        # 参数: {{ ep.params }}
{% endfor %}
        pass

    def send_message(self, user: User, content: dict) -> SendResult:
{% for ep in endpoints if ep.category == "message" %}
        # {{ ep.method }} {{ ep.path }}
{% if ep.pre_steps %}
{% for ps in ep.pre_steps %}
        # 前置: {{ ps.endpoint }} → 提取 {{ ps.extract }} → {{ ps.pass_to }}
{% endfor %}
{% endif %}
{% endfor %}
        pass

    def check_account_health(self) -> HealthStatus:
{% if status_codes %}
        # 已知状态码:
{% for code, desc in status_codes.items() %}
        #   {{ code }}: {{ desc }}
{% endfor %}
{% endif %}
        pass
```

- [ ] **Step 4: 编写 models.py.j2 模板**

`reverse-toolkit/src/toolkit/generator/templates/models.py.j2`:

```jinja2
from dataclasses import dataclass, field
from typing import Optional


{% for ep in endpoints if ep.response_model %}
@dataclass
class {{ ep.response_model|replace("[]","")|capitalize }}:
    # 端点: {{ ep.method }} {{ ep.path }}
    id: str = ""
    name: str = ""
    raw: dict = field(default_factory=dict)
{% endfor %}
```

- [ ] **Step 5: 实现 scaffold.py**

`reverse-toolkit/src/toolkit/generator/scaffold.py`:

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def generate(spec: dict) -> tuple[str, str]:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    # credential hint
    login_params = []
    if spec.get("auth", {}).get("login_flow"):
        for step in spec["auth"]["login_flow"]:
            login_params.extend(step.get("params", {}).keys())
    spec["credential_hint"] = ", ".join(set(login_params)) if login_params else "phone, smsCode"

    plugin_tpl = env.get_template("plugin.py.j2")
    plugin_code = plugin_tpl.render(**spec, capitalize=lambda s: s.capitalize())

    models_tpl = env.get_template("models.py.j2")
    models_code = models_tpl.render(**spec)

    return plugin_code, models_code
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/test_scaffold.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add reverse-toolkit/src/toolkit/generator/ reverse-toolkit/tests/test_scaffold.py
git commit -m "feat: add Jinja2 scaffold generator for plugin.py and models.py"
```

---

### Task 12: proxy — mitmproxy 抓包模块

**Files:**
- Create: `reverse-toolkit/src/toolkit/proxy/addon.py`
- Create: `reverse-toolkit/src/toolkit/proxy/server.py`

- [ ] **Step 1: 实现 mitmproxy addon**

`reverse-toolkit/src/toolkit/proxy/addon.py`:

```python
import json
from datetime import datetime
from pathlib import Path
from mitmproxy import ctx


class FlowRecorder:
    def __init__(self, host_filter: str, output_dir: str):
        self.host_filter = host_filter.replace("*", "")
        self.output_dir = Path(output_dir)
        self.flows: list[dict] = []

    def _should_record(self, flow) -> bool:
        host = flow.request.pretty_host
        return self.host_filter in host

    def request(self, flow):
        if not self._should_record(flow):
            return

    def response(self, flow):
        if not self._should_record(flow):
            return

        req = flow.request
        resp = flow.response

        req_body = ""
        if req.content:
            try:
                req_body = req.content.decode("utf-8", errors="replace")
            except Exception:
                req_body = str(req.content)

        resp_body = ""
        if resp and resp.content:
            try:
                resp_body = resp.content.decode("utf-8", errors="replace")
            except Exception:
                resp_body = str(resp.content)

        headers = {}
        if req.headers:
            for k, v in req.headers.items():
                headers[k] = v

        self.flows.append({
            "request": {
                "method": req.method,
                "path": req.path,
                "host": req.pretty_host,
                "headers": headers,
                "content": req_body,
                "timestamp_start": req.timestamp_start,
            },
            "response": {
                "status_code": resp.status_code if resp else 0,
                "content": resp_body,
                "headers": dict(resp.headers) if resp and resp.headers else {},
            }
        })

    def done(self):
        if not self.flows:
            return
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        out_file = date_dir / f"flows_{ts}.mitm"
        out_file.write_text(json.dumps(self.flows, ensure_ascii=False, indent=2), encoding="utf-8")
        ctx.log.info(f"Saved {len(self.flows)} flows to {out_file}")


# mitmproxy addon 入口
addons = []
```

- [ ] **Step 2: 实现 server.py**

`reverse-toolkit/src/toolkit/proxy/server.py`:

```python
from pathlib import Path
from mitmproxy.options import Options
from mitmproxy.master import Master
from mitmproxy.addons import default_addons
from toolkit.proxy.addon import FlowRecorder
import threading
import sys


def start_proxy(app: str, host_filter: str, output_dir: str, frida_script: str | None = None):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    recorder = FlowRecorder(host_filter=host_filter, output_dir=output_dir)

    opts = Options(listen_host="0.0.0.0", listen_port=8080)
    master = Master(opts)
    master.addons.add(*default_addons())
    master.addons.add(recorder)

    if frida_script:
        print(f"[提示] 请先在目标设备上运行 Frida 脚本: frida -U -f <package> -l {frida_script} --no-pause")
    else:
        frida_dir = Path(__file__).resolve().parent / "frida_scripts"
        print(f"[提示] 可用 Frida SSL Unpin 脚本:")
        for js in frida_dir.glob("*.js"):
            print(f"  frida -U -f <package> -l {js} --no-pause")

    print(f"[代理] 启动在 0.0.0.0:8080")
    print(f"[过滤] 域名: {host_filter}")
    print(f"[输出] {output_dir}")
    print(f"[停止] 按 Ctrl+C 退出")
    print()

    try:
        master.run()
    except KeyboardInterrupt:
        print("\n[代理] 已停止")
        master.shutdown()
```

- [ ] **Step 3: Commit**

```bash
git add reverse-toolkit/src/toolkit/proxy/addon.py reverse-toolkit/src/toolkit/proxy/server.py
git commit -m "feat: add mitmproxy proxy module with flow recording"
```

---

### Task 13: 全链路集成验证 — 使用真实数据

**Files:**
- 无新建文件，验证已有代码

- [ ] **Step 1: 验证 CLI 完整链路**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m toolkit.cli --help
```

Expected: 显示所有命令列表（init, status, analyze, scaffold, proxy-start）

- [ ] **Step 2: 用已有 popo 数据验证分析链路**

假设你已有 mitmproxy 抓包数据。如果数据在 `projects/popo/raw_flows/` 下：

```bash
cd reverse-toolkit && PYTHONPATH=src python -m toolkit.cli analyze --app popo
```

检查输出：`projects/popo/api_spec.json` 和 `projects/popo/api_doc.md` 应正确生成。

- [ ] **Step 3: 验证 scaffold 链路**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m toolkit.cli scaffold --app popo
```

检查输出：`projects/popo/plugin.py` 和 `projects/popo/models.py` 应正确生成，包含 5 个方法签名。

- [ ] **Step 4: Commit**

```bash
git add reverse-toolkit/
git commit -m "verify: full pipeline integration test with popo data"
```

---

### Task 14: Dashboard (FastAPI Web 面板)

**Files:**
- Create: `reverse-toolkit/src/toolkit/web/server.py`
- Create: `reverse-toolkit/src/toolkit/web/templates/index.html`
- Create: `reverse-toolkit/src/toolkit/web/templates/project.html`
- Create: `reverse-toolkit/src/toolkit/web/static/style.css`

- [ ] **Step 1: 实现 FastAPI server.py**

`reverse-toolkit/src/toolkit/web/server.py`:

```python
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from toolkit.db import list_projects, get_project as db_get_project
from toolkit.project import status as project_status, PROJECTS_ROOT

WEB_DIR = Path(__file__).resolve().parent
app = FastAPI(title="逆向工具箱")

app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = []
    for proj_name in [d.name for d in PROJECTS_ROOT.iterdir() if d.is_dir()] if PROJECTS_ROOT.exists() else []:
        projects.append(project_status(proj_name))
    return templates.TemplateResponse("index.html", {"request": request, "projects": projects})


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

    return templates.TemplateResponse("project.html", {
        "request": request,
        "app_name": app_name,
        "status": status,
        "spec": spec_data,
        "notes": notes,
    })
```

- [ ] **Step 2: 实现 index.html**

`reverse-toolkit/src/toolkit/web/templates/index.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>逆向工具箱</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="page-header">
  <h1>逆向工具箱</h1>
  <p class="sub">一键抓包 → 自动分析 → 生成插件骨架</p>
</header>

<div class="toolbar">
  <button class="btn-primary" onclick="alert('TODO: 新建项目表单')">+ 新建项目</button>
</div>

<div class="project-grid">
{% for p in projects %}
  <a href="/project/{{ p.app_name }}" class="project-card">
    <div class="card-header">
      <span class="app-name">{{ p.app_name }}</span>
      <span class="status-badge status-{{ p.db_status }}">{{ p.db_status }}</span>
    </div>
    <div class="card-body">
      <div class="stat-row">
        <span>{{ '已抓包' if p.has_flows else '未抓包' }}</span>
        <span>{{ '已分析' if p.has_spec else '未分析' }}</span>
        <span>{{ '已生成' if p.has_plugin else '未生成' }}</span>
      </div>
    </div>
  </a>
{% endfor %}
{% if not projects %}
  <div class="empty-state">
    <p>暂无项目</p>
    <p class="hint">点击"+ 新建项目"开始</p>
  </div>
{% endif %}
</div>
</body>
</html>
```

- [ ] **Step 3: 实现 project.html**

`reverse-toolkit/src/toolkit/web/templates/project.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ app_name }} - 逆向工具箱</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<header class="page-header">
  <a href="/" class="back-link">&larr; 返回</a>
  <h1>{{ app_name }}</h1>
  <p class="sub">状态: {{ status.db_status }}</p>
</header>

<div class="tab-bar">
  <button class="tab active" onclick="switchTab('overview')">概览</button>
  <button class="tab" onclick="switchTab('endpoints')">API 端点</button>
  <button class="tab" onclick="switchTab('notes')">对抗记录</button>
</div>

<div id="tab-overview" class="tab-content">
  <div class="quick-actions">
    <button class="btn-primary">启动代理抓包</button>
    <button class="btn-secondary">分析流量</button>
    <button class="btn-secondary">生成插件骨架</button>
  </div>
  {% if spec %}
  <div class="info-card">
    <h3>基础信息</h3>
    <p>Base URL: {{ spec.base_url }}</p>
    <p>认证方式: {{ spec.auth.type }}</p>
    <p>端点数量: {{ spec.endpoints|length }}</p>
  </div>
  {% endif %}
</div>

<div id="tab-endpoints" class="tab-content" style="display:none">
  {% if spec %}
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filterCategory('all')">全部</button>
    <button class="filter-btn" onclick="filterCategory('auth')">认证</button>
    <button class="filter-btn" onclick="filterCategory('rooms')">房间</button>
    <button class="filter-btn" onclick="filterCategory('rank')">排行榜</button>
    <button class="filter-btn" onclick="filterCategory('message')">私信</button>
    <button class="filter-btn" onclick="filterCategory('other')">其他</button>
  </div>
  <table class="endpoint-table">
    <thead>
      <tr><th>方法</th><th>路径</th><th>分类</th><th>分页</th></tr>
    </thead>
    <tbody>
    {% for ep in spec.endpoints %}
      <tr data-category="{{ ep.category }}">
        <td><span class="method-badge method-{{ ep.method|lower }}">{{ ep.method }}</span></td>
        <td><code>{{ ep.path }}</code></td>
        <td>{{ ep.category }}</td>
        <td>{{ ep.pagination or '-' }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% endif %}
</div>

<div id="tab-notes" class="tab-content" style="display:none">
  <textarea class="notes-editor" rows="20">{{ notes }}</textarea>
  <button class="btn-primary" style="margin-top:12px">保存</button>
</div>

<script>
function switchTab(name) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).style.display = 'block';
  event.target.classList.add('active');
}
function filterCategory(cat) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.endpoint-table tbody tr').forEach(row => {
    row.style.display = (cat === 'all' || row.dataset.category === cat) ? '' : 'none';
  });
}
</script>
</body>
</html>
```

- [ ] **Step 4: 实现 style.css**

`reverse-toolkit/src/toolkit/web/static/style.css`:

```css
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f1117;color:#e1e4e8;padding:32px;min-height:100vh}
.page-header{margin-bottom:24px}
.page-header h1{font-size:20px;font-weight:600;color:#f0f6fc}
.page-header .sub{color:#8b949e;font-size:13px;margin-top:4px}
.back-link{color:#58a6ff;text-decoration:none;font-size:13px;display:block;margin-bottom:8px}
.toolbar{margin-bottom:20px}
.btn-primary{background:#1f6feb;color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px}
.btn-secondary{background:#21262d;color:#c9d1d1;border:1px solid #30363d;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px}
.project-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.project-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;text-decoration:none;color:inherit;display:block;transition:border-color .15s}
.project-card:hover{border-color:#58a6ff}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.app-name{font-weight:600;color:#f0f6fc;font-size:15px}
.status-badge{font-size:10px;padding:2px 8px;border-radius:10px;text-transform:uppercase}
.status-created{background:#21262d;color:#8b949e}
.status-analyzed{background:#1f6feb20;color:#58a6ff;border:1px solid #1f6feb40}
.status-scaffolded{background:#23863620;color:#3fb950;border:1px solid #23863640}
.stat-row{display:flex;gap:16px;font-size:11px;color:#8b949e}
.empty-state{text-align:center;padding:60px 0;color:#8b949e}
.empty-state .hint{font-size:12px;margin-top:4px;color:#484f58}
.tab-bar{display:flex;gap:4px;margin-bottom:20px;border-bottom:1px solid #21262d;padding-bottom:0}
.tab{background:none;border:none;color:#8b949e;padding:8px 16px;cursor:pointer;font-size:13px;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.active{color:#f0f6fc;border-bottom-color:#58a6ff}
.tab-content{padding-top:12px}
.quick-actions{display:flex;gap:8px;margin-bottom:20px}
.info-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.info-card h3{font-size:14px;color:#f0f6fc;margin-bottom:8px}
.filter-bar{display:flex;gap:6px;margin-bottom:12px}
.filter-btn{background:#21262d;border:1px solid #30363d;color:#8b949e;padding:4px 12px;border-radius:4px;cursor:pointer;font-size:11px}
.filter-btn.active{background:#1f6feb30;border-color:#58a6ff;color:#58a6ff}
.endpoint-table{width:100%;border-collapse:collapse;font-size:12px}
.endpoint-table th{text-align:left;padding:8px 12px;border-bottom:1px solid #30363d;color:#58a6ff;font-size:11px;font-weight:600}
.endpoint-table td{padding:7px 12px;border-bottom:1px solid #21262d;color:#c9d1d9}
.method-badge{font-size:10px;padding:1px 6px;border-radius:4px;font-weight:600}
.method-post{background:#23863620;color:#3fb950}
.method-get{background:#1f6feb20;color:#58a6ff}
code{font-family:'SF Mono',Consolas,monospace;font-size:11px;background:#0d1117;padding:1px 5px;border-radius:3px;color:#d2a8ff}
.notes-editor{width:100%;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d1;padding:12px;font-family:'SF Mono',Consolas,monospace;font-size:12px;line-height:1.6;resize:vertical}
```

- [ ] **Step 5: 在 CLI 中添加 dashboard 命令**

在 `reverse-toolkit/src/toolkit/cli.py` 末尾添加：

```python
@main.command()
@click.option("--port", default=9734, help="监听端口")
@click.option("--no-open", is_flag=True, help="不自动打开浏览器")
def dashboard(port, no_open):
    """启动 Web 管理面板"""
    import uvicorn
    import webbrowser
    from toolkit.web.server import app as fastapi_app

    if not no_open:
        webbrowser.open(f"http://localhost:{port}")
    uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="info")
```

- [ ] **Step 6: 验证 Dashboard 启动**

```bash
cd reverse-toolkit && PYTHONPATH=src python -m toolkit.cli dashboard --no-open
```

Expected: FastAPI 启动在 `http://127.0.0.1:9734`，访问首页显示项目列表。

- [ ] **Step 7: Commit**

```bash
git add reverse-toolkit/src/toolkit/web/ reverse-toolkit/src/toolkit/cli.py
git commit -m "feat: add FastAPI dashboard with project list and detail pages"
```

---

### Task 15: kb/notes.py — 知识库笔记管理

**Files:**
- Create: `reverse-toolkit/src/toolkit/kb/notes.py`

- [ ] **Step 1: 实现 notes.py**

`reverse-toolkit/src/toolkit/kb/notes.py`:

```python
from pathlib import Path
from toolkit.project import get_project_dir


def read_notes(app_name: str) -> str:
    notes_path = get_project_dir(app_name) / "notes.md"
    if notes_path.exists():
        return notes_path.read_text(encoding="utf-8")
    return ""


def append_note(app_name: str, text: str):
    notes_path = get_project_dir(app_name) / "notes.md"
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {timestamp}\n\n{text}\n"
    current = read_notes(app_name) if notes_path.exists() else f"# {app_name} 对抗记录\n"
    notes_path.write_text(current + entry, encoding="utf-8")


def edit_notes(app_name: str, content: str):
    notes_path = get_project_dir(app_name) / "notes.md"
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    notes_path.write_text(content, encoding="utf-8")
```

- [ ] **Step 2: 在 CLI 中添加 kb note 命令**

在 `reverse-toolkit/src/toolkit/cli.py` 中添加：

```python
@main.group()
def kb():
    """反调知识库管理"""
    pass

@kb.command()
@click.option("--app", required=True, help="APP 名称")
def note(app):
    """添加/编辑对抗笔记"""
    from toolkit.kb.notes import read_notes
    notes = read_notes(app)
    # 打开默认编辑器或打印现有笔记
    click.echo(f"=== {app} 对抗记录 ===")
    click.echo(notes if notes else "(空)")
    click.echo("\n使用 toolkit kb edit --app <app> 编辑笔记")
```

- [ ] **Step 3: Commit**

```bash
git add reverse-toolkit/src/toolkit/kb/ reverse-toolkit/src/toolkit/cli.py
git commit -m "feat: add knowledge base notes management"
```

---

## 验证清单

完成所有 Task 后执行：

```bash
# 1. 全量单元测试
cd reverse-toolkit && PYTHONPATH=src python -m pytest tests/ -v

# 2. CLI 可访问
PYTHONPATH=src python -m toolkit.cli --help

# 3. 端到端（需真实数据）
PYTHONPATH=src python -m toolkit.cli init --app popo
PYTHONPATH=src python -m toolkit.cli analyze --app popo
PYTHONPATH=src python -m toolkit.cli scaffold --app popo
PYTHONPATH=src python -m toolkit.cli status-cmd --app popo

# 4. Dashboard 启动
PYTHONPATH=src python -m toolkit.cli dashboard --no-open
```
