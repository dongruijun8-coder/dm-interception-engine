"""Plugin auto-discovery."""
import importlib.util
from pathlib import Path
from engine.plugin_base import BasePlugin


def discover_plugins() -> dict[str, type[BasePlugin]]:
    """Scan engine/plugins/ directory and return {app_name: PluginClass}."""
    plugins = {}
    plugins_dir = Path(__file__).parent
    for entry in plugins_dir.iterdir():
        if entry.is_dir() and (entry / "plugin.py").exists():
            spec = importlib.util.spec_from_file_location(
                f"engine.plugins.{entry.name}.plugin",
                str(entry / "plugin.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (isinstance(attr, type) and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin):
                    plugins[attr.app_name] = attr  # type: ignore
    return plugins


def load_plugin(app_name: str) -> BasePlugin:
    """Instantiate a plugin by app name."""
    plugins = discover_plugins()
    if app_name not in plugins:
        raise ValueError(f"Plugin '{app_name}' not found. Available: {list(plugins.keys())}")
    return plugins[app_name]()
