# 截流私信运行引擎

基于插件架构的多平台私信自动化引擎，支持零代码接入新 APP。

## 架构

```
engine/
├── main.py              # FastAPI 入口
├── plugin_base.py       # 插件基类 (5 个抽象方法)
├── generic_plugin.py    # 通用插件 — 读 api_spec.json 即可运行
├── pipeline.py          # 6 步流水线编排
├── filters.py           # 可组合用户过滤器
├── templates.py         # 消息模板管理
├── db.py                # SQLite 异步数据库
├── models.py            # 数据模型定义
├── router_dashboard.py  # Dashboard API 路由
├── plugins/             # 自定义插件目录
│   ├── __init__.py      # 插件发现 & 加载
│   └── popo/            # 漂漂 APP 插件
└── static/
    └── index.html       # Dashboard SPA 界面
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m engine.main
# 访问 http://127.0.0.1:8765
```

## 接入新 APP

**方式一：Spec 驱动（零代码）**

在 Dashboard 的「APP 管理」中上传 `api_spec.json`，GenericPlugin 自动解析并运行。

**方式二：自定义插件**

在 `engine/plugins/<app_name>/` 下创建 `plugin.py`，继承 `BasePlugin` 实现 5 个方法：

```python
from engine.plugin_base import BasePlugin

class MyPlugin(BasePlugin):
    app_name = "myapp"

    async def authenticate(self, credential): ...
    async def fetch_rooms(self, session, filters): ...
    async def fetch_users(self, session, room): ...
    async def send_message(self, session, user, message): ...
    async def check_health(self, session): ...
```

## 流水线

```
认证 → 健康检查 → 拉取房间 → 拉取用户 → 过滤 → 发送私信
```

## API

| 路由 | 说明 |
|------|------|
| `GET /api/apps` | 列出已接入 APP |
| `POST /api/apps` | 注册新 APP (spec) |
| `DELETE /api/apps/{name}` | 移除 APP |
| `GET /api/accounts` | 账号列表 |
| `POST /api/accounts` | 创建账号 |
| `GET /api/tasks` | 任务列表 |
| `POST /api/tasks` | 创建任务 |
| `POST /api/tasks/{id}/run` | 执行任务 |
| `GET /api/templates/{app}` | 获取消息模板 |
| `PUT /api/templates/{app}` | 更新消息模板 |
| `GET /api/stats` | 统计数据 |

## 测试

```bash
pytest engine/tests/ -v
```
