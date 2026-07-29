"""Regression tests for the result-entry delta check (comparing a new numeric result to the
patient's previous result for the same parameter) and for a pre-existing bug where a saved draft's
values never got pre-filled when the entry form was reopened."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, result_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_compute_delta_percent_basic():
    assert result_service.compute_delta_percent(150, 100) == 50.0
    assert result_service.compute_delta_percent(100, 100) == 0.0


def test_compute_delta_percent_returns_none_without_a_previous_value():
    assert result_service.compute_delta_percent(100, None) is None
    assert result_service.compute_delta_percent(100, 0) is None


def _order_id_for_visit(visit_id):
    conn = db.get_connection()
    order = conn.execute("SELECT id FROM visit_test_orders WHERE visit_id = ?", (visit_id,)).fetchone()
    conn.close()
    return order["id"]


def test_get_order_entry_view_exposes_previous_numeric_result(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    test_id = tests[0]["id"]

    visit1 = visit_service.create_visit(
        patient={"full_name": "مريض دلتا", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[test_id],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    order1_id = _order_id_for_visit(visit1["id"])
    entry1 = result_service.get_order_entry_view(order1_id)
    param = entry1["parameters"][0]
    assert param["previous_numeric"] is None

    result_service.save_results(
        order1_id,
        [{"parameter_id": p["parameter_id"], "numeric_value": 10, "text_value": None,
          "low": p["range_low"], "high": p["range_high"], "normal_text": p["range_text"],
          "data_type": p["data_type"]} for p in entry1["parameters"]],
        mark_completed=True, user_id=user.user_id,
    )

    visit2 = visit_service.create_visit(
        patient={"full_name": "مريض دلتا 2", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[test_id],
        existing_patient_id=visit1["patient_id"], discount=0, initial_payment=0, user_id=user.user_id,
    )
    order2_id = _order_id_for_visit(visit2["id"])
    entry2 = result_service.get_order_entry_view(order2_id)
    param2 = entry2["parameters"][0]
    assert param2["previous_numeric"] == 10


def test_reopening_a_draft_prefills_its_saved_values(tmp_path, monkeypatch):
    """Regression: get_order_entry_view() returns keys 'existing_numeric'/'existing_text', which
    is what results_view.py's load_order() must read to prefill the entry form."""
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit = visit_service.create_visit(
        patient={"full_name": "مريض مسودة", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )
    order_id = _order_id_for_visit(visit["id"])
    entry = result_service.get_order_entry_view(order_id)
    param = entry["parameters"][0]

    result_service.save_results(
        order_id,
        [{"parameter_id": param["parameter_id"], "numeric_value": 42, "text_value": None,
          "low": param["range_low"], "high": param["range_high"], "normal_text": param["range_text"],
          "data_type": param["data_type"]}],
        mark_completed=False, user_id=user.user_id,
    )

    reopened = result_service.get_order_entry_view(order_id)
    reopened_param = next(p for p in reopened["parameters"] if p["parameter_id"] == param["parameter_id"])
    assert reopened_param["existing_numeric"] == 42
