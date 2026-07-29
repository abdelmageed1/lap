"""Regression test for reports_service.get_period_comparison(): month-to-date vs the same
day-range last month, and year-to-date vs the same day-range last year."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, reports_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_period_comparison_counts_a_visit_created_today_in_the_current_month_and_year(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit_service.create_visit(
        patient={"full_name": "مريض مقارنة", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=20, user_id=user.user_id,
    )

    comparison = reports_service.get_period_comparison()
    assert comparison["month"]["current"]["visit_count"] == 1
    assert comparison["month"]["current"]["revenue"] > 0
    assert comparison["year"]["current"]["visit_count"] == 1
    assert comparison["month"]["previous"]["visit_count"] == 0
    assert comparison["month"]["revenue_change_pct"] is None  # previous is 0, undefined % change


def test_period_comparison_computes_percentage_change_against_a_nonzero_previous_period(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()

    last_month_visit = visit_service.create_visit(
        patient={"full_name": "مريض الشهر الماضي", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    conn = db.get_connection()
    conn.execute("UPDATE visits SET visit_date = datetime('now', '-1 month')")
    conn.commit()
    conn.close()

    this_month_visit = visit_service.create_visit(
        patient={"full_name": "مريض هذا الشهر", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"], tests[1]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )

    comparison = reports_service.get_period_comparison()
    assert comparison["month"]["previous"]["revenue"] == last_month_visit["total"]
    assert comparison["month"]["current"]["revenue"] == this_month_visit["total"]
    expected_pct = (this_month_visit["total"] - last_month_visit["total"]) / last_month_visit["total"] * 100
    assert comparison["month"]["revenue_change_pct"] == expected_pct
