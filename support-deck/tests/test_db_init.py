def test_init_db_creates_tables(tmp_path):
    from src.db import init_db, connect

    db = tmp_path / "t.db"
    init_db(db)
    con = connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"queue_items", "approval_actions", "explainers", "frequency_buckets"}.issubset(names)
