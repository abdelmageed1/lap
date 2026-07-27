from app import db
from app.services import catalog_service, visit_service


def test_create_visit_writes_audit_logs(tmp_path, monkeypatch):
    """Regression test: log_action() used to always open its own connection and commit, which
    deadlocks (and is silently swallowed by the try/except around every call site) when invoked
    from inside create_visit() - that function holds its own open write transaction on a second
    connection to the same SQLite file. Passing conn=conn through to log_action fixed it; this
    test fails again if that wiring is ever dropped.
    """
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    tests = catalog_service.search_tests("CBC")
    assert tests, "expected the seeded catalog to contain a CBC test"
    test_id = tests[0]["id"]

    patient = {"full_name": "Audit Test Patient", "title": "السيد /", "gender": "Male",
               "age_years": 30, "phone": ""}
    visit = visit_service.create_visit(patient, None, None, [test_id], 0, 0)

    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT table_name, action FROM audit_logs WHERE table_name IN ('patients', 'visits', 'visit_test_orders')"
        ).fetchall()
        logged_tables = {r["table_name"] for r in rows}
        assert logged_tables == {"patients", "visits", "visit_test_orders"}, (
            f"expected audit rows for patients/visits/visit_test_orders, got: {logged_tables}"
        )
    finally:
        conn.close()
