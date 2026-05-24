"""SQLite database init and async CRUD operations."""
import aiosqlite
import json
from contextlib import asynccontextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "engine.db"


@asynccontextmanager
async def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS app_account (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                phone TEXT,
                token TEXT,
                session_data TEXT DEFAULT '{}',
                health_status TEXT DEFAULT 'ok',
                last_health_check TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL REFERENCES app_account(id),
                app_name TEXT NOT NULL,
                trigger TEXT DEFAULT 'manual',
                status TEXT DEFAULT 'pending',
                config TEXT DEFAULT '{}',
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS fetched_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL REFERENCES task(id),
                app_name TEXT NOT NULL,
                app_uid TEXT NOT NULL,
                name TEXT,
                gender TEXT,
                room_id TEXT,
                room_type TEXT,
                rank INTEGER,
                score INTEGER,
                extra TEXT DEFAULT '{}',
                raw_data TEXT DEFAULT '{}',
                UNIQUE(task_id, app_uid)
            );

            CREATE TABLE IF NOT EXISTS send_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES fetched_user(id),
                task_id INTEGER NOT NULL REFERENCES task(id),
                message_body TEXT,
                success INTEGER DEFAULT 0,
                error_code TEXT,
                error_msg TEXT,
                cost_ms INTEGER,
                sent_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS task_stat (
                task_id INTEGER PRIMARY KEY REFERENCES task(id),
                rooms_fetched INTEGER DEFAULT 0,
                users_fetched INTEGER DEFAULT 0,
                users_deduped INTEGER DEFAULT 0,
                msg_sent INTEGER DEFAULT 0,
                msg_success INTEGER DEFAULT 0,
                msg_failed INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()


# ── Account CRUD ──

async def create_account(app_name: str, phone: str = "", token: str = "", session_data: dict = None) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO app_account (app_name, phone, token, session_data) VALUES (?, ?, ?, ?)",
            (app_name, phone, token, json.dumps(session_data or {}))
        )
        await db.commit()
        return cursor.lastrowid


async def get_account(account_id: int) -> dict:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM app_account WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["session_data"] = json.loads(d["session_data"])
        return d


async def get_accounts_by_app(app_name: str) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM app_account WHERE app_name = ?", (app_name,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_account_token(account_id: int, token: str, session_data: dict):
    async with get_db() as db:
        await db.execute(
            "UPDATE app_account SET token = ?, session_data = ?, updated_at = datetime('now') WHERE id = ?",
            (token, json.dumps(session_data or {}), account_id)
        )
        await db.commit()


async def update_account_health(account_id: int, status: str):
    async with get_db() as db:
        await db.execute(
            "UPDATE app_account SET health_status = ?, last_health_check = datetime('now'), updated_at = datetime('now') WHERE id = ?",
            (status, account_id)
        )
        await db.commit()


# ── Task CRUD ──

async def create_task(account_id: int, app_name: str, config: dict) -> int:
    async with get_db() as db:
        await db.execute("BEGIN")
        try:
            cursor = await db.execute(
                "INSERT INTO task (account_id, app_name, config) VALUES (?, ?, ?)",
                (account_id, app_name, json.dumps(config))
            )
            row_id = cursor.lastrowid
            await db.execute("INSERT INTO task_stat (task_id) VALUES (?)", (row_id,))
            await db.commit()
            return row_id
        except:
            await db.rollback()
            raise


async def update_task_status(task_id: int, status: str):
    async with get_db() as db:
        extra = ""
        if status == "running":
            extra = ", started_at = datetime('now')"
        elif status in ("done", "failed"):
            extra = ", finished_at = datetime('now')"
        await db.execute(f"UPDATE task SET status = ?{extra} WHERE id = ?", (status, task_id))
        await db.commit()


async def get_task(task_id: int) -> dict:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM task WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["config"] = json.loads(d["config"])
        return d


async def list_tasks(limit: int = 20) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT t.*, s.rooms_fetched, s.users_fetched, s.users_deduped, s.msg_sent, s.msg_success, s.msg_failed "
            "FROM task t LEFT JOIN task_stat s ON t.id = s.task_id ORDER BY t.created_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── User CRUD ──

async def insert_user(task_id: int, app_name: str, user) -> bool:
    """Insert user if not exists for this task. Returns True if inserted, False if duplicate."""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO fetched_user (task_id, app_name, app_uid, name, gender, room_id, room_type, rank, score, extra, raw_data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task_id, app_name, user.app_uid, user.name, user.gender, user.room_id,
                 user.room_type, user.rank, user.score, json.dumps(user.extra), json.dumps(user.raw))
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_task_users(task_id: int) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM fetched_user WHERE task_id = ?", (task_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def count_task_users(task_id: int) -> int:
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM fetched_user WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        return row["cnt"]


# ── Send Log CRUD ──

async def log_send(user_id: int, task_id: int, message_body: str, result) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO send_log (user_id, task_id, message_body, success, error_code, error_msg, cost_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, task_id, message_body, int(result.success), result.error_code, result.error_msg, result.cost_ms)
        )
        await db.commit()
        return cursor.lastrowid


async def get_sent_app_uids(app_name: str) -> set[str]:
    """Get all app_uids that have been sent to (for skip_sent filter)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT DISTINCT fu.app_uid FROM send_log sl "
            "JOIN fetched_user fu ON sl.user_id = fu.id "
            "WHERE fu.app_name = ?",
            (app_name,)
        )
        rows = await cursor.fetchall()
        return {r["app_uid"] for r in rows}


# ── Stat CRUD ──

async def update_task_stat(task_id: int, **kwargs):
    if not kwargs:
        async with get_db() as db:
            await db.execute("UPDATE task_stat SET updated_at = datetime('now') WHERE task_id = ?", (task_id,))
            await db.commit()
        return

    async with get_db() as db:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [task_id]
        await db.execute(
            f"UPDATE task_stat SET {sets}, updated_at = datetime('now') WHERE task_id = ?",
            values
        )
        await db.commit()


async def get_task_stat(task_id: int) -> dict:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM task_stat WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
