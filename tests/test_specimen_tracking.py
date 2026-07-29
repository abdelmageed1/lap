"""Regression tests for specimen (sample) collection-stage tracking."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, specimen_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def _order_id_for_visit(visit_id):
    conn = db.get_connection()
    order = conn.execute("SELECT id FROM visit_test_orders WHERE visit_id = ?", (visit_id,)).fetchone()
    conn.close()
    return order["id"]


def test_new_order_starts_at_not_collected(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit = visit_service.create_visit(
        patient={"full_name": "مريض عينة", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    order_id = _order_id_for_visit(visit["id"])
    pending = specimen_service.get_pending_specimens()
    assert any(p["order_id"] == order_id and p["specimen_status"] == "NotCollected" for p in pending)


def test_advance_specimen_status_moves_through_every_stage(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit = visit_service.create_visit(
        patient={"full_name": "مريض عينة 2", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    order_id = _order_id_for_visit(visit["id"])

    expected_sequence = ["Collected", "ReceivedInLab", "InTesting", "Completed"]
    for expected_stage in expected_sequence:
        ok, _ = specimen_service.advance_specimen_status(order_id, user_id=user.user_id)
        assert ok
        conn = db.get_connection()
        current = conn.execute("SELECT specimen_status FROM visit_test_orders WHERE id = ?", (order_id,)).fetchone()
        conn.close()
        assert current["specimen_status"] == expected_stage


def test_advancing_past_completed_fails_gracefully(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit = visit_service.create_visit(
        patient={"full_name": "مريض عينة 3", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    order_id = _order_id_for_visit(visit["id"])
    for _ in range(4):
        specimen_service.advance_specimen_status(order_id, user_id=user.user_id)

    ok, message = specimen_service.advance_specimen_status(order_id, user_id=user.user_id)
    assert ok is False

    pending = specimen_service.get_pending_specimens()
    assert not any(p["order_id"] == order_id for p in pending)
