"""Test plugin loading and abstract interface."""
import pytest
from engine.plugin_base import BasePlugin
from engine.plugins import discover_plugins


def test_discover_popo_plugin():
    plugins = discover_plugins()
    assert "popo" in plugins
    assert issubclass(plugins["popo"], BasePlugin)


def test_instantiate_plugin():
    plugins = discover_plugins()
    p = plugins["popo"]()
    assert p.app_name == "popo"


def test_base_plugin_cannot_instantiate():
    with pytest.raises(TypeError):
        BasePlugin()
