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
    finally:
        conn.close()

    # Test create user, update fullname, delete user
    ok, msg = user_service.create_user("temp_user", "مستخدم مؤقت", "pass123", role_id)
    assert ok is True

    users = user_service.get_users()
    u = next(x for x in users if x["username"] == "temp_user")

    ok_up, msg_up = user_service.update_user_full_name(u["id"], "اسم جديد معدل")
    assert ok_up is True

    ok_un, msg_un = user_service.update_username(u["id"], "temp_user_new")
    assert ok_un is True

    ok_del, msg_del = user_service.delete_user(u["id"])
    assert ok_del is True



