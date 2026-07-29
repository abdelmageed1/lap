"""Regression test for reports_service.get_turnaround_time_analytics(): average time from order
creation to reviewer approval, derived from existing audit_logs timestamps (no schema change)."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, reports_service, result_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def _order_id_for_visit(visit_id):
    conn = db.get_connection()
    order = conn.execute("SELECT id FROM visit_test_orders WHERE visit_id = ?", (visit_id,)).fetchone()
    conn.close()
    return order["id"]


def test_tat_only_counts_reviewed_orders_and_computes_positive_duration(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    test_id = tests[0]["id"]

    visit = visit_service.create_visit(
        patient={"full_name": "مريض TAT", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[test_id],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    order_id = _order_id_for_visit(visit["id"])

    # Not yet reviewed - must not appear in TAT stats.
    assert reports_service.get_turnaround_time_analytics() == []

    entry = result_service.get_order_entry_view(order_id)
    result_service.save_results(
        order_id,
        [{"parameter_id": p["parameter_id"], "numeric_value": 5, "text_value": None,
          "low": p["range_low"], "high": p["range_high"], "normal_text": p["range_text"],
          "data_type": p["data_type"]} for p in entry["parameters"]],
        mark_completed=True, user_id=user.user_id,
    )
    result_service.approve_order(order_id, user_id=user.user_id)

    stats = reports_service.get_turnaround_time_analytics()
    assert len(stats) == 1
    row = stats[0]
    assert row["test_id"] == test_id
    assert row["completed_count"] == 1
    assert row["avg_hours"] >= 0
    assert row["max_hours"] >= 0
