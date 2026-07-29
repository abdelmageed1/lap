"""Regression test: reception should be able to detect that a patient already had the exact same
test done recently, so it can warn the staff before an unnecessary repeat is added to a visit."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_recent_test_dates_matches_same_patient_same_test(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()

    visit = visit_service.create_visit(
        patient={"full_name": "مريض متكرر", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )

    recent = visit_service.get_recent_test_dates(visit["patient_id"], tests[0]["id"])
    assert len(recent) == 1


def test_recent_test_dates_does_not_match_a_different_test(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()

    visit = visit_service.create_visit(
        patient={"full_name": "مريض آخر", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )

    recent = visit_service.get_recent_test_dates(visit["patient_id"], tests[1]["id"])
    assert recent == []


def test_recent_test_dates_ignores_visits_older_than_the_window(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()

    visit = visit_service.create_visit(
        patient={"full_name": "مريض قديم", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )

    conn = db.get_connection()
    conn.execute("UPDATE visits SET visit_date = datetime('now', '-10 days') WHERE id = ?", (visit["id"],))
    conn.commit()
    conn.close()

    recent = visit_service.get_recent_test_dates(visit["patient_id"], tests[0]["id"], within_days=3)
    assert recent == []


def test_recent_test_dates_returns_empty_for_no_patient_id():
    assert visit_service.get_recent_test_dates(None, 1) == []
