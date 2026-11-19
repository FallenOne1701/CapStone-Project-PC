from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS queue_items (
    question_id TEXT PRIMARY KEY,
    question_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    draft TEXT,
    citation_url TEXT,
    routing_note TEXT,
    searched_json TEXT NOT NULL DEFAULT '[]',
    reviewer_flags_json TEXT NOT NULL DEFAULT '[]',
    explainer_id TEXT,
    agent_package_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS approval_actions (
    action_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    payload_preview_json TEXT NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_approval',
    edited_content TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS explainers (
    explainer_id TEXT PRIMARY KEY,
    bullets_json TEXT NOT NULL DEFAULT '[]',
    links_json TEXT NOT NULL DEFAULT '[]',
    last_checked TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS frequency_buckets (
    bucket_id TEXT PRIMARY KEY,
    normalized_text TEXT NOT NULL UNIQUE,
    count INTEGER NOT NULL DEFAULT 0,
    window_start TEXT,
    window_end TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def ensure_agent_package_column(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(queue_items)")}
    if "agent_package_json" not in cols:
        con.execute(
            "ALTER TABLE queue_items ADD COLUMN agent_package_json TEXT NOT NULL DEFAULT '{}'"
        )


def init_db(path: str | Path) -> None:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = connect(db_path)
    try:
        con.executescript(SCHEMA_SQL)
        ensure_agent_package_column(con)
        con.commit()
    finally:
        con.close()
