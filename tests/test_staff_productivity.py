"""Regression test: staff productivity analytics must count visits/payments per staff member.

visit_service.create_visit()'s log_action('visits', visit_id, 'create', ...) call used to omit
user_id entirely, so every visit's audit row was logged with user_id=NULL. reports_service's staff
productivity query filters audit_logs by 'visits'/'create' AND user_id = <staff id>, which could
never match NULL - so every staff member always showed 0 visits created and 0 collected payments
in the "Reports & Statistics" -> staff productivity chart, no matter how many visits they actually
registered."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, reports_service, result_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_create_visit_records_the_creating_user_in_the_audit_log(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)

    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    assert tests, "seed data must include at least one active test"

    visit = visit_service.create_visit(
        patient={"full_name": "مريض تجريبي", "gender": "Male", "age_years": 30},
        doctor_id=None,
        referral_source_id=None,
        test_ids=[tests[0]["id"]],
        discount=0,
        initial_payment=10,
        user_id=user.user_id,
    )

    stats = reports_service.get_staff_productivity_analytics()
    admin_stats = next(s for s in stats if s["user_id"] == user.user_id)
    assert admin_stats["visits_created"] >= 1
    assert admin_stats["collected_payments"] >= 10

    visit_service.add_payment(visit["id"], 5, user_id=user.user_id)
    stats_after = reports_service.get_staff_productivity_analytics()
    admin_stats_after = next(s for s in stats_after if s["user_id"] == user.user_id)
    assert admin_stats_after["collected_payments"] >= 15


def test_completing_results_is_counted_as_results_processed_for_that_user(tmp_path, monkeypatch):
    """save_results() used to never write a table_name='results' audit row at all - it only ever
    logged to 'result_values'/'visit_test_orders' - so reports_service's "results processed" query
    (which filters on table_name='results') could never match anything, no matter who entered or
    approved results."""
    _init(tmp_path, monkeypatch)

    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit = visit_service.create_visit(
        patient={"full_name": "مريض تجريبي 2", "gender": "Male", "age_years": 40},
        doctor_id=None,
        referral_source_id=None,
        test_ids=[tests[0]["id"]],
        discount=0,
        initial_payment=0,
        user_id=user.user_id,
    )

    from app import db as _db
    conn = _db.get_connection()
    order = conn.execute(
        "SELECT id FROM visit_test_orders WHERE visit_id = ?", (visit["id"],)
    ).fetchone()
    order_id = order["id"]
    conn.close()

    entry = result_service.get_order_entry_view(order_id)
    values = [
        {"parameter_id": p["parameter_id"], "numeric_value": 5, "text_value": None,
         "low": p["range_low"], "high": p["range_high"], "normal_text": p["range_text"],
         "data_type": p["data_type"]}
        for p in entry["parameters"]
    ]
    result_service.save_results(order_id, values, mark_completed=True, user_id=user.user_id)

    stats = reports_service.get_staff_productivity_analytics()
    admin_stats = next(s for s in stats if s["user_id"] == user.user_id)
    assert admin_stats["results_processed"] >= 1

    # The query counts DISTINCT order rows, not individual actions, so approving the same
    # already-completed order doesn't double the count - it stays at 1.
    result_service.approve_order(order_id, user_id=user.user_id)
    stats_after = reports_service.get_staff_productivity_analytics()
    admin_stats_after = next(s for s in stats_after if s["user_id"] == user.user_id)
    assert admin_stats_after["results_processed"] == 1
