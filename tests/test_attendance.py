"""Regression tests for staff attendance (check-in/check-out)."""
from app import db
from app.seed import seed_if_empty
from app.services import attendance_service, auth_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_check_in_then_check_out(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")

    assert attendance_service.get_open_session(user.user_id) is None

    ok, _ = attendance_service.check_in(user.user_id)
    assert ok
    open_session = attendance_service.get_open_session(user.user_id)
    assert open_session is not None
    assert open_session["check_out"] is None

    ok, _ = attendance_service.check_out(user.user_id)
    assert ok
    assert attendance_service.get_open_session(user.user_id) is None


def test_cannot_check_in_twice_without_checking_out(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")

    attendance_service.check_in(user.user_id)
    ok, message = attendance_service.check_in(user.user_id)
    assert ok is False
    assert "مفتوح" in message


def test_cannot_check_out_without_checking_in(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    ok, _ = attendance_service.check_out(user.user_id)
    assert ok is False


def test_attendance_report_computes_hours_worked(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    attendance_service.check_in(user.user_id)

    conn = db.get_connection()
    conn.execute(
        "UPDATE attendance SET check_in = datetime('now', '-2 hours') WHERE user_id = ?",
        (user.user_id,),
    )
    conn.commit()
    conn.close()

    attendance_service.check_out(user.user_id)
    report = attendance_service.get_attendance_report()
    assert len(report) == 1
    assert report[0]["hours_worked"] == 2.0
    assert report[0]["full_name"]
