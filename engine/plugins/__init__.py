"""Plugin auto-discovery."""
import importlib.util
import json
from pathlib import Path
from engine.plugin_base import BasePlugin
from engine.generic_plugin import GenericPlugin

SPECS_DIR = Path(__file__).parent.parent.parent / "data" / "api_specs"


def discover_plugins() -> dict[str, type[BasePlugin]]:
    """Scan engine/plugins/ directory AND data/api_specs/ for available plugins.
    Returns {app_name: PluginClass}. Custom plugins override spec-driven ones."""
    plugins = {}

    # 1. Discover custom Python plugins
    plugins_dir = Path(__file__).parent
    for entry in plugins_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith("_") and (entry / "plugin.py").exists():
            spec = importlib.util.spec_from_file_location(
                f"engine.plugins.{entry.name}.plugin",
                str(entry / "plugin.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type) and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin and attr is not GenericPlugin):
                    plugins[attr.app_name] = attr

    # 2. Discover spec-driven plugins (api_spec.json files)
    if SPECS_DIR.exists():
        for spec_file in SPECS_DIR.glob("*.json"):
            try:
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_data = json.load(f)
                app_name = spec_data.get("app", spec_file.stem)
                if app_name not in plugins:  # Don't override custom plugins
                    plugins[app_name] = GenericPlugin
            except Exception:
                pass  # Skip invalid spec files

    return plugins


def load_plugin(app_name: str) -> BasePlugin:
    """Instantiate a plugin by app name."""
    plugins = discover_plugins()
    if app_name not in plugins:
        raise ValueError(f"Plugin '{app_name}' not found. Available: {list(plugins.keys())}")

    plugin_cls = plugins[app_name]

    # If it's the GenericPlugin class, load the spec and pass it
    if plugin_cls is GenericPlugin:
        if SPECS_DIR.exists():
            for spec_file in SPECS_DIR.glob("*.json"):
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_data = json.load(f)
                if spec_data.get("app") == app_name:
                    return GenericPlugin(spec_data)
    else:
        return plugin_cls()

    raise ValueError(f"Could not find spec for '{app_name}'")
