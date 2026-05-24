# 逆向工具箱 — 设计规格说明书

**日期:** 2026-05-24
**状态:** 已确认
**范围:** 逆向工具箱（运行引擎为独立项目，通过 api_spec.json 串联）

---

## 1. 项目概述

为直播/社交类 APP 的逆向分析提供平台化工具链：一键抓包 → 自动分析 → 生成插件骨架。输出为标准 `api_spec.json`，供运行引擎消费。

**使用场景:** 单人使用，每个 APP 持续迭代分析。

---

## 2. 架构总览

```
┌─────────────────────────────────────────────────────┐
│                  逆向工具箱                           │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐      │
│  │ 代理抓包  │  │ 流量分析  │  │ 骨架代码生成  │      │
│  │ proxy/   │→ │analyzer/ │→ │ generator/   │      │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘      │
│       │             │               │               │
│  ┌────▼─────────────▼───────────────▼──────────┐    │
│  │              schema.py (共享契约)             │    │
│  │           project.py (项目管理)              │    │
│  └─────────────────────────────────────────────┘    │
│                       │                             │
│  ┌────────────────────▼────────────────────────┐    │
│  │          Dashboard (FastAPI + HTML)          │    │
│  │          localhost:9734                      │    │
│  └─────────────────────────────────────────────┘    │
│                       │                             │
│                 输出: api_spec.json                   │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │   运行引擎       │
              │  (独立项目)      │
              └─────────────────┘
```

三个核心模块之间**禁止直接 import**，完全通过文件系统交换数据。

辅助资源（原"反调知识库"）分散到各处：
- Frida/SSL unpin 脚本 → `src/toolkit/proxy/frida_scripts/`
- APP 对抗记录 → 各项目目录下的 `notes.md`
- APK 静态扫描 → 独立 CLI 命令 `toolkit apk-scan`

---

## 3. 模块间数据流与接口契约

### 3.1 数据流

```
用户操作 APP ──→ mitmproxy ──→ raw_flows/*.mitm
                                   │
                            analyzer/FlowParser
                                   │
                              api_spec.json + api_doc.md
                                   │
                            generator/Jinja2
                                   │
                              plugin.py + models.py
```

### 3.2 接口 1：proxy → analyzer（文件）

**传输格式:** mitmproxy 原生 dump 文件 (`.mitm`)
**存储位置:** `projects/<app>/raw_flows/<date>/`

```python
# analyzer 内部解析后的中间表示（不落地为文件）
CapturedRequest = {
    method: str,
    path: str,
    host: str,
    req_headers: dict,
    req_body: str,
    resp_status: int,
    resp_body: str,
    content_type: str,
    timestamp: float,
}
```

### 3.3 接口 2：api_spec.json（核心契约）

**位置:** `projects/<app>/api_spec.json`
**Schema 定义:** `src/toolkit/schema.py`（Python dataclass，唯一定义源）

```python
@dataclass
class ApiSpec:
    app: str
    version: str
    base_url: str
    auth: AuthInfo
    common_params: CommonParams
    endpoints: list[EndpointDef]
    status_codes: dict[str, str]
    anti_reverse: AntiReverseInfo

@dataclass
class AuthInfo:
    type: str                         # "token" | "cookie" | "oauth" | "none"
    login_flow: list[LoginStep]

@dataclass
class LoginStep:
    order: int
    endpoint: str
    method: str                       # 默认 "POST"
    params: dict
    extract: str | None               # 从响应中提取的字段名

@dataclass
class CommonParams:
    headers: dict[str, str]
    body: list[str]                   # 公共 body 字段名列表
    url_params: list[str]

@dataclass
class EndpointDef:
    name: str                         # 语义化标识
    method: str
    path: str
    category: str                     # auth|rooms|rank|message|profile|other
    params: dict
    pagination: str | None            # offset_limit|page_num|cursor|None
    response_model: str | None        # "rooms[]" 等
    pre_steps: list[PreStep] | None

@dataclass
class PreStep:
    endpoint: str
    extract: str
    pass_to: str

@dataclass
class AntiReverseInfo:
    ssl_pinning: bool
    encryption: str                   # 描述或 "none"
    device_fingerprint: str           # 描述或 "none"
    captcha: str                      # 描述或 "none"
    notes: str
```

### 3.4 接口 3：generator 输出

**输入:** `api_spec.json`
**输出:** `projects/<app>/plugin.py` + `projects/<app>/models.py`

generator 只读 api_spec.json，不关心其来源。生成的 plugin.py 继承运行引擎的 BasePlugin 基类，实现 5 个方法签名。

---

## 4. 项目管理设计

### 4.1 Project 作为一等公民

每个 APP 对应一个项目目录：

```
projects/
  <app-name>/
    raw_flows/           # mitmproxy dump 文件，按日期子目录
      2026-05-19/
      2026-05-22/
    api_spec.json        # 分析结果（核心产出）
    api_doc.md           # 人类可读 API 文档
    plugin.py            # 骨架代码
    models.py            # 数据模型
    notes.md             # 对抗记录、特殊发现
```

### 4.2 SQLite 元数据

`reverse-toolkit/toolkit.db` 记录项目状态：

| 表 | 用途 |
|----|------|
| `project` | app_name, version, base_url, status, created_at, updated_at |
| `endpoint_cache` | 缓存已分析的端点，支持增量分析 |
| `scan_log` | 操作日志（proxy/analyze/scaffold 执行记录） |

### 4.3 CLI 以项目为中心

```bash
toolkit project init <app>           # 创建项目骨架
toolkit project status <app>         # 查看项目状态
toolkit proxy start --project <app>  # 抓包（流量自动归入项目）
toolkit analyze --project <app>      # 分析（读 raw_flows → 写 api_spec.json）
toolkit scaffold --project <app>     # 生成（读 api_spec.json → 写 plugin.py）
toolkit kb note --project <app>      # 添加对抗笔记
toolkit apk-scan --file <apk>        # 静态扫描 APK
toolkit dashboard                    # 启动 Web 面板
```

---

## 5. Dashboard 设计

### 5.1 技术选型

**方案:** FastAPI + 纯 HTML/CSS + 少量 vanilla JS（alpine.js 或 HTMX）

- 命令: `toolkit dashboard` 启动本地服务 `localhost:9734`，自动打开浏览器
- 数据直读 SQLite + 项目文件系统
- 不引入构建工具，代码量 ~300 行后端 + ~500 行前端

### 5.2 页面结构

```
首页：项目列表
├── 项目卡片网格（状态标签：抓包中 / 已分析 / 已生成）
├── 新建项目按钮 + 导入项目
└── 辅助工具快速入口（APK扫描、Frida脚本库）

项目详情页（单 APP）
├── 概览 Tab：基础信息 + 快捷操作按钮
├── API 端点 Tab：按分类表格（筛选/搜索/展开详情）
├── 分析报告 Tab：api_doc.md 渲染视图
└── 对抗记录 Tab：notes.md 编辑区
```

### 5.3 视觉风格

沿用 mockups 的暗色主题：
- 背景 `#0f1117`，卡片 `#161b22`，边框 `#30363d`
- 强调色 `#58a6ff`，成功色 `#3fb950`，警告色 `#d29922`
- 字体: system-ui + monospace（代码块用 SF Mono / Consolas）

---

## 6. 项目目录结构

```
reverse-toolkit/
  docs/superpowers/specs/       # 设计文档
  src/toolkit/
    __init__.py
    cli.py                      # Click CLI 入口
    schema.py                   # api_spec 共享数据结构
    project.py                  # 项目管理逻辑
    db.py                       # SQLite 操作
    proxy/
      __init__.py
      server.py                 # mitmproxy 启动 + 过滤
      addon.py                  # 自定义 mitmproxy addon
      frida_scripts/            # 通用解 SSL pinning 脚本
        ssl_unpin.js
        ssl_unpin_native.js
    analyzer/
      __init__.py
      flow_parser.py            # 读取 .mitm 文件
      endpoint_extractor.py     # 提取 + 去重 API 端点
      classifier.py             # 按 URL 规则分类
      spec_builder.py           # 组装 ApiSpec → 写入 JSON
      doc_generator.py          # 生成 Markdown 文档
    generator/
      __init__.py
      scaffold.py               # 读 api_spec，渲染模板
      templates/
        plugin.py.j2
        models.py.j2
    web/
      __init__.py
      server.py                 # FastAPI 应用
      templates/                # HTML 页面
        index.html
        project.html
      static/                   # 暗色主题 CSS
    kb/
      __init__.py
      apk_scanner.py            # APK 静态扫描（加固/检测库识别）
      notes.py                  # 项目 notes.md 管理
  projects/                     # 各 APP 项目数据
  tests/
  requirements.txt
  README.md
```

---

## 7. 技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | mitmproxy/Frida 生态都是 Python |
| 代理 | mitmproxy (Python API) | 可编程控制、自动过滤、流量导出 |
| 分析 | Python 标准库 + 正则 | 解析 JSON 请求/响应，模式识别 |
| 骨架生成 | Jinja2 | 模板渲染 plugin.py / models.py |
| CLI | Click | 子命令组织、参数校验 |
| Web | FastAPI + 纯 HTML | 轻量、直读 SQLite、无需构建 |
| 存储 | SQLite + JSON 文件 | 单人用零配置 |
| 包管理 | pip + requirements.txt | 简单够用 |

---

## 8. 实施步骤

### Step 1: 项目初始化
- 创建 `reverse-toolkit/` 目录结构
- `requirements.txt`: mitmproxy, click, jinja2, fastapi, uvicorn
- 搭建 CLI 入口骨架 (`cli.py` + `setup.py` 或 `pyproject.toml`)

### Step 2: schema + project 基础层
- 实现 `schema.py`（ApiSpec 及所有 dataclass）
- 实现 `project.py`（init/status/目录管理）
- 实现 `db.py`（SQLite 初始化 + 基本 CRUD）

### Step 3: 代理抓包模块
- 实现 mitmproxy addon：域名过滤 + flow 保存
- 实现 `toolkit proxy start --project <app>` CLI
- 集成 Frida 脚本提示

### Step 4: 流量分析模块
- FlowParser: 解析 mitmproxy dump
- EndpointExtractor: 去重 + 结构化
- Classifier: URL 规则分类
- SpecBuilder: 组装 ApiSpec → api_spec.json
- DocGenerator: 生成 Markdown 文档

### Step 5: 骨架代码生成
- 编写 Jinja2 模板
- 实现 scaffold 命令

### Step 6: Dashboard
- FastAPI server + 路由
- 首页 HTML（项目列表）
- 项目详情页 HTML（Tab 切换、端点表格、Markdown 渲染）
- `toolkit dashboard` 启动命令

### Step 7: 辅助工具
- APK 静态扫描
- 知识库 notes 管理

---

## 9. 验证方案

1. 用已有漂漂 (popo) APP 的 mitmproxy 流量作为测试输入
2. `toolkit project init popo` → 创建项目骨架
3. `toolkit analyze --project popo` → 生成 `api_spec.json`
4. 验证 api_spec.json 与手动分析的 `api_analysis.md` 信息一致
5. `toolkit scaffold --project popo` → 生成 plugin.py
6. 验证骨架代码的 5 个方法签名与运行引擎 BasePlugin 兼容
7. `toolkit dashboard` → 浏览器打开，项目列表可交互

---

## 10. 与运行引擎的边界

```
逆向工具箱（本项目）               运行引擎（独立项目）
─────────────────────           ─────────────────────
产物: api_spec.json      ──→    输入: api_spec.json
产物: plugin.py          ──→    输入: 加载为插件
产物: models.py          ──→    输入: 数据模型
```

两个工具各有一个 Dashboard（localhost:9734 / localhost:9735），独立启动，共享 `projects/` 目录。
