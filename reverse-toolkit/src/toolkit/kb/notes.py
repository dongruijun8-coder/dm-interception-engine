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
