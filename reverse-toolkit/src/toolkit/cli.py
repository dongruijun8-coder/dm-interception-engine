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


@main.command(name="status-cmd")
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
    import json
    from dataclasses import asdict

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
    import json

    proj = get_project_dir(app)
    spec_path = proj / "api_spec.json"
    if not spec_path.exists():
        click.echo(f"错误: {app} 没有 api_spec.json，请先运行 analyze")
        return

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


if __name__ == "__main__":
    main()
