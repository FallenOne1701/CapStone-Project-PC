def test_init_db_creates_tables(tmp_path):
    from src.db import init_db, connect

    db = tmp_path / "t.db"
    init_db(db)
    con = connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"queue_items", "approval_actions", "explainers", "frequency_buckets"}.issubset(names)


def test_queue_items_has_agent_package_json(tmp_path):
    from src.db import init_db, connect

    db = tmp_path / "t.db"
    init_db(db)
    con = connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(queue_items)")}
    con.close()
    assert "agent_package_json" in cols


def test_ensure_agent_package_column_on_legacy_db(tmp_path):
    """Existing DB created without the column still gains it on init_db."""
    import sqlite3
    from src.db import init_db, connect

    db = tmp_path / "legacy.db"
    con = sqlite3.connect(str(db))
    con.execute(
        """
        CREATE TABLE queue_items (
            question_id TEXT PRIMARY KEY,
            question_text TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            draft TEXT,
            citation_url TEXT,
            routing_note TEXT,
            searched_json TEXT NOT NULL DEFAULT '[]',
            reviewer_flags_json TEXT NOT NULL DEFAULT '[]',
            explainer_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    con.commit()
    con.close()
    init_db(db)
    con = connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(queue_items)")}
    con.close()
    assert "agent_package_json" in cols
