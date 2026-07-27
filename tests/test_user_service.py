from app import db
from app.services import user_service


def test_create_role_and_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()

    role_id = user_service.create_role("TestRole")
    assert isinstance(role_id, int)

    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        assert row is not None
        audit = conn.execute(
            "SELECT * FROM audit_logs WHERE table_name='roles' AND row_id = ?", (role_id,)
        ).fetchone()
        assert audit is not None
    finally:
        conn.close()
