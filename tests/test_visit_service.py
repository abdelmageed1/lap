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


def test_delete_patient_removes_records_and_audits(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis_del.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    from app.services import auth_service
    seed_if_empty()

    tests = catalog_service.search_tests("CBC")
    test_id = tests[0]["id"]

    patient = {"full_name": "Delete Target Patient", "title": "السيد /", "gender": "Male",
               "age_years": 40, "phone": "01000000000"}
    visit = visit_service.create_visit(patient, None, None, [test_id], 0, 50.0)

    conn = db.get_connection()
    patient_row = conn.execute("SELECT id FROM patients WHERE full_name = ?", ("Delete Target Patient",)).fetchone()
    patient_id = patient_row["id"]
    conn.close()

    # Test Admin password verification
    assert auth_service.verify_admin_password("Admin@123") is True
    assert auth_service.verify_admin_password("WrongPass") is False

    # Perform patient deletion
    ok, msg = visit_service.delete_patient(patient_id, user_id=1)
    assert ok is True
    assert "Delete Target Patient" in msg

    # Verify database state
    conn = db.get_connection()
    try:
        p_count = conn.execute("SELECT COUNT(*) c FROM patients WHERE id = ?", (patient_id,)).fetchone()["c"]
        v_count = conn.execute("SELECT COUNT(*) c FROM visits WHERE patient_id = ?", (patient_id,)).fetchone()["c"]
        assert p_count == 0
        assert v_count == 0

        # Check audit log for deletion action
        audit = conn.execute("SELECT * FROM audit_logs WHERE table_name = 'patients' AND action = 'delete'").fetchone()
        assert audit is not None
        assert "Delete Target Patient" in audit["details"]
    finally:
        conn.close()


def test_export_and_import_patients_data(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis_io.db"))
    db.init_schema()

    # Import new patients
    sample_patients = [
        {"full_name": "مريض جديد 1", "phone": "01111111111", "gender": "Male", "age_years": 35},
        {"full_name": "مريض جديد 2", "phone": "01222222222", "gender": "Female", "age_years": 28},
    ]
    created, updated, msg = visit_service.import_patients_data(sample_patients)
    assert created == 2
    assert updated == 0

    # Test export
    exported = visit_service.export_patients_data()
    assert len(exported) == 2
    names = {p["full_name"] for p in exported}
    assert "مريض جديد 1" in names
    assert "مريض جديد 2" in names

    # Import duplicate to test update / deduplication
    created2, updated2, msg2 = visit_service.import_patients_data([
        {"full_name": "مريض جديد 1", "phone": "01111111111", "gender": "Male", "age_years": 36}
    ])
    assert created2 == 0
    assert updated2 == 1


