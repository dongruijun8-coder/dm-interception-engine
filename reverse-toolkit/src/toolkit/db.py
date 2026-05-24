import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "toolkit.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL UNIQUE,
            version TEXT,
            base_url TEXT,
            status TEXT DEFAULT 'created',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS endpoint_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            host TEXT NOT NULL,
            category TEXT,
            first_seen_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(app_name, method, path)
        );

        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()

def insert_project(app_name: str, version: str = "", base_url: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO project (app_name, version, base_url, status, updated_at) "
        "VALUES (?, ?, ?, 'created', datetime('now','localtime'))",
        (app_name, version, base_url)
    )
    conn.commit()
    conn.close()

def update_project_status(app_name: str, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE project SET status=?, updated_at=datetime('now','localtime') WHERE app_name=?",
        (status, app_name)
    )
    conn.commit()
    conn.close()

def list_projects() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM project ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_project(app_name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM project WHERE app_name=?", (app_name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def insert_scan_log(app_name: str, action: str, detail: str = ""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO scan_log (app_name, action, detail) VALUES (?, ?, ?)",
        (app_name, action, detail)
    )
    conn.commit()
    conn.close()
