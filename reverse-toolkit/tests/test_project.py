import tempfile
from pathlib import Path
from unittest.mock import patch
from toolkit.project import init_project, get_project_dir, PROJECTS_ROOT

def test_init_project_creates_directories():
    with tempfile.TemporaryDirectory() as tmp:
        projects_root = Path(tmp)
        with patch('toolkit.project.PROJECTS_ROOT', projects_root):
            init_project("testapp")
            proj_dir = projects_root / "testapp"
            assert proj_dir.is_dir()
            assert (proj_dir / "raw_flows").is_dir()
            assert (proj_dir / "notes.md").is_file()
