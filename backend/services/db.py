import sqlite3
from pathlib import Path

from backend.config import Config
from backend.models.schema import SCHEMA_SQL


def _connect():
    Path(Config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_db(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
    if "snapshot_path" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN snapshot_path TEXT")
    if "has_snapshot" not in columns:
        conn.execute("ALTER TABLE events ADD COLUMN has_snapshot INTEGER NOT NULL DEFAULT 0")

    columns = {row[1] for row in conn.execute("PRAGMA table_info(lamp_states)").fetchall()}
    if columns and "manual_override_until" not in columns:
        conn.execute("ALTER TABLE lamp_states ADD COLUMN manual_override_until INTEGER DEFAULT 0")


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate_db(conn)
        conn.commit()


def execute(query, params=()):
    with _connect() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def fetch_one(query, params=()):
    with _connect() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_all(query, params=()):
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
