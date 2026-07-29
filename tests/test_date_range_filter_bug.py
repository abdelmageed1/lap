"""Regression test for a widespread date-range filtering bug: every report/search function that
filtered an end_date with a literal "{end_date} 23:59:59" string compared against a 'T'-separated
ISO timestamp column (e.g. visit_date stored as "2026-07-29T12:20:37") silently excluded every
record from that entire day. This is because 'T' (0x54) sorts after ' ' (0x20) in a plain string
comparison, so "...T12:20:37" > "...  23:59:59" is always true regardless of the actual time of
day - meaning the "<=" end-date check always failed for same-day records. In practice this meant
the "اليوم" (today) preset filter in Reports & Statistics, and any single-day date range anywhere
in the app, always returned zero rows. Fixed by comparing date(column) instead of the raw string."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, reports_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def _today():
    conn = db.get_connection()
    today = conn.execute("SELECT date('now')").fetchone()[0]
    conn.close()
    return today


def test_same_day_date_range_includes_visits_created_today(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    doctors_list = catalog_service.get_doctors()
    doctor_id = doctors_list[0]["id"] if doctors_list else None
    visit_service.create_visit(
        patient={"full_name": "مريض اليوم", "gender": "Male", "age_years": 30},
        doctor_id=doctor_id, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=15, user_id=user.user_id,
    )

    today = _today()
    visits = reports_service.get_visits_in_range(start_date=today, end_date=today)
    assert len(visits) == 1

    if doctor_id:
        doctors = reports_service.get_top_referring_doctors(start_date=today, end_date=today)
        assert sum(d["visit_count"] for d in doctors) == 1

    sources = reports_service.get_referral_sources_analytics(start_date=today, end_date=today)
    assert sum(s["visit_count"] for s in sources) == 1

    departments = reports_service.get_department_revenue_breakdown(start_date=today, end_date=today)
    assert sum(d["order_count"] for d in departments) == 1

    staff = reports_service.get_staff_productivity_analytics(start_date=today, end_date=today)
    admin_stats = next(s for s in staff if s["user_id"] == user.user_id)
    assert admin_stats["visits_created"] == 1


def test_same_day_range_finds_patients_via_search_patients(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit_service.create_visit(
        patient={"full_name": "مريض بحث اليوم", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )

    today = _today()
    results = visit_service.search_patients(start_date=today, end_date=today)
    assert any(p["full_name"] == "مريض بحث اليوم" for p in results)
