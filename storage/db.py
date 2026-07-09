"""SQLite connection helper. Single db file at repo root: expansion.db."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "expansion.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def insert_raw_listing(conn: sqlite3.Connection, city_id: str, corridor: str, source: str, raw_text: str, price_raw: str | None) -> int:
    cur = conn.execute(
        "INSERT INTO raw_listings (city_id, corridor, source, raw_text, price_raw, scraped_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (city_id, corridor, source, raw_text, price_raw, datetime.now(timezone.utc).isoformat()),
    )
    return cur.lastrowid
