"""SQLite-based history database for paper deduplication."""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "history.db")


def _get_db_path() -> str:
    path = os.path.abspath(DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            arxiv_id TEXT PRIMARY KEY,
            doi TEXT,
            title TEXT,
            status TEXT DEFAULT 'pending',
            score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            searched_at TEXT NOT NULL,
            days_searched INTEGER,
            papers_found INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def is_seen(arxiv_id: str) -> bool:
    """Check if a paper has already been processed."""
    conn = _connect()
    cur = conn.execute("SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,))
    result = cur.fetchone() is not None
    conn.close()
    return result


def batch_filter_new(arxiv_ids: list[str]) -> list[str]:
    """Return only arxiv_ids that are NOT in the database."""
    if not arxiv_ids:
        return []
    conn = _connect()
    placeholders = ",".join("?" for _ in arxiv_ids)
    cur = conn.execute(
        f"SELECT arxiv_id FROM papers WHERE arxiv_id IN ({placeholders})", arxiv_ids
    )
    seen = {row[0] for row in cur.fetchall()}
    conn.close()
    return [aid for aid in arxiv_ids if aid not in seen]


def insert_paper(arxiv_id: str, doi: str = "", title: str = "",
                 status: str = "pending", score: float = 0.0):
    """Insert a new paper record."""
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO papers (arxiv_id, doi, title, status, score) VALUES (?, ?, ?, ?, ?)",
        (arxiv_id, doi, title, status, score),
    )
    conn.commit()
    conn.close()


def update_status(arxiv_id: str, status: str, score: float | None = None):
    """Update paper status (pending -> scored -> read -> reported)."""
    conn = _connect()
    now = datetime.utcnow().isoformat()
    if score is not None:
        conn.execute(
            "UPDATE papers SET status = ?, score = ?, updated_at = ? WHERE arxiv_id = ?",
            (status, score, now, arxiv_id),
        )
    else:
        conn.execute(
            "UPDATE papers SET status = ?, updated_at = ? WHERE arxiv_id = ?",
            (status, now, arxiv_id),
        )
    conn.commit()
    conn.close()


def get_papers_by_status(status: str) -> list[dict]:
    """Get all papers with a given status."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM papers WHERE status = ? ORDER BY score DESC", (status,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


# First ever search starts from this date
EPOCH = "2026-01-01T00:00:00"


def get_last_search_time() -> datetime:
    """Get the timestamp of the last search. Returns EPOCH if never searched."""
    conn = _connect()
    cur = conn.execute("SELECT searched_at FROM search_log ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row:
        return datetime.fromisoformat(row[0])
    return datetime.fromisoformat(EPOCH)


def record_search(days_searched: int, papers_found: int):
    """Record a search event with current timestamp."""
    conn = _connect()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO search_log (searched_at, days_searched, papers_found) VALUES (?, ?, ?)",
        (now, days_searched, papers_found),
    )
    conn.commit()
    conn.close()
