from app import db
from app.services import catalog_service, result_service, visit_service


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()


def test_entry_then_review_then_approve_workflow(tmp_path, monkeypatch):
    """Regression test for the entry/review split: an order must not be printable (Reviewed)
    until a reviewer explicitly approves it - saving with mark_completed=True should only move it
    to 'Completed' (awaiting review), never straight to 'Reviewed'."""
    _setup(tmp_path, monkeypatch)

    tests = catalog_service.search_tests("CBC")
    test_id = tests[0]["id"]
    patient = {"full_name": "Review Test Patient", "title": "", "gender": "Male", "age_years": 25, "phone": ""}
    visit = visit_service.create_visit(patient, None, None, [test_id], 0, 0)
    order_id = visit_service.get_visit_details(visit["id"])["orders"][0]["id"]

    # Still in the entry queue before any results are saved.
    assert any(o["id"] == order_id for o in result_service.get_pending_orders(limit=500))
    assert not any(o["id"] == order_id for o in result_service.get_orders_pending_review(limit=500))

    entry = result_service.get_order_entry_view(order_id)
    values = [{"parameter_id": p["parameter_id"], "numeric_value": 5.0, "text_value": None,
               "low": p["range_low"], "high": p["range_high"], "normal_text": p.get("range_text"),
               "data_type": p["data_type"]} for p in entry["parameters"]]
    result_service.save_results(order_id, values, mark_completed=True)

    # Marking "completed" must move it to the review queue, not straight to printable/Reviewed.
    assert not any(o["id"] == order_id for o in result_service.get_pending_orders(limit=500))
    assert any(o["id"] == order_id for o in result_service.get_orders_pending_review(limit=500))

    data_before_approval = result_service.get_report_data(order_id)
    assert data_before_approval["status"] == "Completed"

    result_service.approve_order(order_id, user_id=None)

    assert not any(o["id"] == order_id for o in result_service.get_orders_pending_review(limit=500))
    data_after_approval = result_service.get_report_data(order_id)
    assert data_after_approval["status"] == "Reviewed"


def test_reject_sends_back_to_entry_queue(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    tests = catalog_service.search_tests("CBC")
    test_id = tests[0]["id"]
    patient = {"full_name": "Reject Test Patient", "title": "", "gender": "Male", "age_years": 25, "phone": ""}
    visit = visit_service.create_visit(patient, None, None, [test_id], 0, 0)
    order_id = visit_service.get_visit_details(visit["id"])["orders"][0]["id"]

    entry = result_service.get_order_entry_view(order_id)
    values = [{"parameter_id": p["parameter_id"], "numeric_value": 1.0, "text_value": None,
               "low": p["range_low"], "high": p["range_high"], "normal_text": p.get("range_text"),
               "data_type": p["data_type"]} for p in entry["parameters"]]
    result_service.save_results(order_id, values, mark_completed=True)

    result_service.send_back_for_edit(order_id, user_id=None)

    assert any(o["id"] == order_id for o in result_service.get_pending_orders(limit=500))
    assert not any(o["id"] == order_id for o in result_service.get_orders_pending_review(limit=500))


def test_create_visit_reuses_existing_patient(tmp_path, monkeypatch):
    """Regression test: picking an existing patient at reception must attach the new visit to the
    same patients row, not create a duplicate - otherwise the Patient History screen would never
    find more than one visit per patient."""
    _setup(tmp_path, monkeypatch)
    tests = catalog_service.search_tests("CBC")
    test_id = tests[0]["id"]

    patient = {"full_name": "Repeat Patient", "title": "", "gender": "Male", "age_years": 40, "phone": "0100"}
    first_visit = visit_service.create_visit(patient, None, None, [test_id], 0, 0)
    patient_id = first_visit["patient_id"]

    second_visit = visit_service.create_visit(
        patient, None, None, [test_id], 0, 0, existing_patient_id=patient_id,
    )
    assert second_visit["patient_id"] == patient_id

    conn = db.get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) c FROM patients WHERE phone = '0100'").fetchone()["c"]
    finally:
        conn.close()
    assert count == 1, "expected no duplicate patient row after reusing existing_patient_id"

    history = result_service.get_patient_history(patient_id)
    assert len(history) == 2


def test_dashboard_snapshot_has_week_and_month_metrics(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    snapshot = visit_service.dashboard_snapshot()
    assert "visits_week" in snapshot
    assert "revenue_week" in snapshot
    assert "visits_month" in snapshot
    assert "revenue_month" in snapshot


def test_patient_result_summary_reports_availability(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    tests = catalog_service.search_tests("CBC")
    test_id = tests[0]["id"]

    patient = {"full_name": "Result Status Patient", "title": "", "gender": "Female", "age_years": 30, "phone": "0111"}
    visit = visit_service.create_visit(patient, None, None, [test_id], 0, 0)
    patient_id = visit["patient_id"]

    summary = result_service.get_patient_result_summary(patient_id)
    assert summary["has_results"] is False
    assert summary["result_status"] == "غير متوفرة"

    order_id = visit_service.get_visit_details(visit["id"])["orders"][0]["id"]
    entry = result_service.get_order_entry_view(order_id)
    values = [{"parameter_id": p["parameter_id"], "numeric_value": 4.5, "text_value": None,
               "low": p["range_low"], "high": p["range_high"], "normal_text": p.get("range_text"),
               "data_type": p["data_type"]} for p in entry["parameters"]]
    result_service.save_results(order_id, values, mark_completed=True)

    summary_after = result_service.get_patient_result_summary(patient_id)
    assert summary_after["has_results"] is True
    assert summary_after["result_status"] == "متوفرة"
    assert summary_after["latest_test_name"]
