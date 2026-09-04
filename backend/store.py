# backend/store.py
"""Thread persistence.

Deliberately at the server boundary and nowhere near the graph: the LangGraph
pipeline stays a pure function of its input, which is what keeps `main.py`
runnable headless and lets the tests stub a node without a database in scope.
Nothing in agents/ imports this module.

SQLite rather than Postgres because a thread is ~50KB of JSON, there is no
concurrency to speak of, and nothing ever queries inside the payload. One
table, one file, one volume — no second service, pool, or migration tool. The
API surface below is the part that matters; swapping the engine later doesn't
change it.

Identity is client-generated (a UUID from the browser), so there is no user
table and no login. An unguessable id makes a thread *shareable*, not private:
anyone holding the link can read it.
"""
import asyncio
import json
import os
import re
import sqlite3
import time
from typing import Optional

DB_PATH = os.environ.get("TARKA_DB", "/data/tarka.db")

# Client-generated UUIDs. Validated as a shape rather than trusted — the
# queries are parameterised, but a malformed id has no business reaching them.
ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

MAX_PAYLOAD_BYTES = 2 * 1024 * 1024  # a thread with 30 sources runs ~50KB
MAX_TITLE = 300


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    # WAL lets a read proceed while a write is in flight, which matters once
    # more than one request is in the air.
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_sync() -> None:
    directory = os.path.dirname(DB_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS threads (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL DEFAULT '',
                payload    TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at)")
    print(f"[STORE] SQLite ready at {DB_PATH}")


def _save_sync(thread_id: str, title: str, payload: dict) -> dict:
    blob = json.dumps(payload, separators=(",", ":"))
    if len(blob.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload too large")

    now = time.time()
    with _connect() as conn:
        # Upsert keeps created_at from the original insert.
        conn.execute(
            """
            INSERT INTO threads (id, title, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (thread_id, title[:MAX_TITLE], blob, now, now),
        )
    return {"id": thread_id, "updated_at": now}


def _load_sync(thread_id: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, title, payload, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "title": row["title"],
        "payload": json.loads(row["payload"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _delete_sync(thread_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    return cur.rowcount > 0


# sqlite3 is blocking; these calls are sub-millisecond but the event loop is
# shared with in-flight SSE streams, so they go to a worker thread anyway.
async def init() -> None:
    await asyncio.to_thread(_init_sync)


async def save(thread_id: str, title: str, payload: dict) -> dict:
    return await asyncio.to_thread(_save_sync, thread_id, title, payload)


async def load(thread_id: str) -> Optional[dict]:
    return await asyncio.to_thread(_load_sync, thread_id)


async def delete(thread_id: str) -> bool:
    return await asyncio.to_thread(_delete_sync, thread_id)


def valid_id(thread_id: str) -> bool:
    return bool(ID_RE.match(thread_id or ""))
