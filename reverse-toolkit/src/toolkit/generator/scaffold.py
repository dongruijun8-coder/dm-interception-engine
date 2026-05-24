from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def generate(spec: dict) -> tuple[str, str]:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    login_params = []
    if spec.get("auth", {}).get("login_flow"):
        for step in spec["auth"]["login_flow"]:
            login_params.extend(step.get("params", {}).keys())
    ctx = dict(spec)
    ctx["credential_hint"] = ", ".join(set(login_params)) if login_params else "phone, smsCode"

    plugin_tpl = env.get_template("plugin.py.j2")
    plugin_code = plugin_tpl.render(**ctx, capitalize=lambda s: s.capitalize())

    models_tpl = env.get_template("models.py.j2")
    models_code = models_tpl.render(**ctx)

    return plugin_code, models_code
