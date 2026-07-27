from app import db


def test_init_schema_creates_audit_table(tmp_path, monkeypatch):
    # db.py binds DATABASE_PATH into its own namespace via `from app.config import DATABASE_PATH`,
    # so it must be patched on `db` itself - patching app.config.DATABASE_PATH (or the APPDATA env
    # var) has no effect here since that name was already resolved at import time.
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))

    db.init_schema()

    conn = db.get_connection()
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        row = cur.fetchone()
        assert row is not None, "audit_logs table should exist"
    finally:
        conn.close()
