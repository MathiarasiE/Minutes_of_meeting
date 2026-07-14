import sqlite3
import time
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS meetings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT,
            started_at  REAL,
            ended_at    REAL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id      INTEGER NOT NULL,
            chunk_index     INTEGER NOT NULL,
            audio_path      TEXT,
            transcript      TEXT,
            created_at      REAL,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        );

        CREATE TABLE IF NOT EXISTS summaries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id  INTEGER NOT NULL,
            kind        TEXT CHECK(kind IN ('intermediate','final')),
            content     TEXT,
            created_at  REAL,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        );
        """)
    print("[DB] Initialized.")


def create_meeting(title: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO meetings (title, started_at) VALUES (?, ?)",
            (title, time.time())
        )
        return cur.lastrowid


def end_meeting(meeting_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE meetings SET ended_at = ? WHERE id = ?",
            (time.time(), meeting_id)
        )


def save_chunk(meeting_id: int, chunk_index: int, audio_path: str, transcript: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO chunks (meeting_id, chunk_index, audio_path, transcript, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (meeting_id, chunk_index, audio_path, transcript, time.time())
        )
        return cur.lastrowid


def save_summary(meeting_id: int, kind: str, content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO summaries (meeting_id, kind, content, created_at) VALUES (?, ?, ?, ?)",
            (meeting_id, kind, content, time.time())
        )
        return cur.lastrowid


def get_all_transcripts(meeting_id: int) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT transcript FROM chunks WHERE meeting_id = ? ORDER BY chunk_index",
            (meeting_id,)
        ).fetchall()
    return [r["transcript"] for r in rows if r["transcript"]]


def get_meeting(meeting_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()


def list_meetings():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM meetings ORDER BY started_at DESC").fetchall()


def get_summaries(meeting_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM summaries WHERE meeting_id = ? ORDER BY created_at",
            (meeting_id,)
        ).fetchall()