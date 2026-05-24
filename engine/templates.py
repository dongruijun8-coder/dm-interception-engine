"""Message template storage and random selection."""
import json
import random
from pathlib import Path

TEMPLATES_FILE = Path(__file__).parent.parent / "data" / "message_templates.json"


def _load() -> dict[str, list[str]]:
    """Load templates grouped by app_name. Returns {app_name: [template_str, ...]}."""
    if TEMPLATES_FILE.exists():
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(data: dict[str, list[str]]):
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_templates(app_name: str) -> list[str]:
    return _load().get(app_name, [])


def set_templates(app_name: str, templates: list[str]):
    data = _load()
    data[app_name] = templates
    _save(data)


def add_template(app_name: str, template: str):
    data = _load()
    if app_name not in data:
        data[app_name] = []
    data[app_name].append(template)
    _save(data)


def remove_template(app_name: str, index: int):
    data = _load()
    if app_name in data and 0 <= index < len(data[app_name]):
        data[app_name].pop(index)
        _save(data)


def pick_random(app_name: str, user_name: str = None) -> str | None:
    """Randomly select a template for the given app. Optionally substitute {name}."""
    templates = get_templates(app_name)
    if not templates:
        return None
    tpl = random.choice(templates)
    if user_name:
        tpl = tpl.replace("{name}", user_name)
    return tpl
