"""Regression tests for the seed-data migration that keeps an already-seeded install's catalog in
sync with new entries added to profiles.json later (Creatinine Clearance breakdown, CBC's Color
Index, Thyroid Function's breakdown) without ever discarding a result a technician already entered."""
from app import db
from app.seed import seed_if_empty


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()


def test_fresh_seed_gives_creatinine_clearance_breakdown_and_cbc_color_index(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    seed_if_empty()

    conn = db.get_connection()
    try:
        cc_test = conn.execute("SELECT id FROM tests WHERE name = 'Creatinine Clearance'").fetchone()
        cc_params = {r["name"] for r in conn.execute(
            "SELECT name FROM test_parameters WHERE test_id = ?", (cc_test["id"],)
        ).fetchall()}
        assert cc_params == {"Serum Creatinine", "Urine Creatinine", "Urine Volume", "Creatinine Clearance"}

        cbc_test = conn.execute("SELECT id FROM tests WHERE name = 'CBC'").fetchone()
        cbc_params = {r["name"] for r in conn.execute(
            "SELECT name FROM test_parameters WHERE test_id = ?", (cbc_test["id"],)
        ).fetchall()}
        assert "Color Index" in cbc_params
    finally:
        conn.close()


def test_backfill_applies_breakdown_to_already_seeded_generic_test(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    from app import seed as seed_module

    conn = db.get_connection()
    seed_module._seed_roles_and_admin(conn)
    seed_module._seed_catalog(conn)  # deliberately skip _seed_profiles, like a pre-upgrade database
    conn.close()

    conn = db.get_connection()
    cc_test = conn.execute("SELECT id FROM tests WHERE name = 'Creatinine Clearance'").fetchone()
    before = conn.execute(
        "SELECT name FROM test_parameters WHERE test_id = ?", (cc_test["id"],)
    ).fetchall()
    assert [r["name"] for r in before] == ["النتيجة"]
    conn.close()

    seed_if_empty()

    conn = db.get_connection()
    try:
        after = {r["name"] for r in conn.execute(
            "SELECT name FROM test_parameters WHERE test_id = ?", (cc_test["id"],)
        ).fetchall()}
        assert after == {"Serum Creatinine", "Urine Creatinine", "Urine Volume", "Creatinine Clearance"}
    finally:
        conn.close()


def test_backfill_handles_test_names_with_trailing_punctuation(tmp_path, monkeypatch):
    """Regression test: the catalog's real test name is "Thyroid Function." (trailing period), but
    its profiles.json attachKey is "thyroidfunction" (no period). An earlier version of the
    backfill's name-to-key normalization only stripped spaces/hyphens/underscores, so it produced
    "thyroidfunction." (period kept) - which never matched, and this test's breakdown silently
    never got backfilled onto an already-installed database."""
    _init(tmp_path, monkeypatch)
    from app import seed as seed_module

    conn = db.get_connection()
    seed_module._seed_roles_and_admin(conn)
    seed_module._seed_catalog(conn)
    conn.close()

    conn = db.get_connection()
    thyroid_test = conn.execute("SELECT id FROM tests WHERE name = 'Thyroid Function.'").fetchone()
    assert thyroid_test is not None
    before = conn.execute(
        "SELECT name FROM test_parameters WHERE test_id = ?", (thyroid_test["id"],)
    ).fetchall()
    assert [r["name"] for r in before] == ["النتيجة"]
    conn.close()

    seed_if_empty()

    conn = db.get_connection()
    try:
        after = {r["name"] for r in conn.execute(
            "SELECT name FROM test_parameters WHERE test_id = ?", (thyroid_test["id"],)
        ).fetchall()}
        assert "النتيجة" not in after
        assert len(after) > 1
    finally:
        conn.close()


def test_backfill_never_discards_a_result_already_entered(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    from app import seed as seed_module

    conn = db.get_connection()
    seed_module._seed_roles_and_admin(conn)
    seed_module._seed_catalog(conn)
    cc_test = conn.execute("SELECT id FROM tests WHERE name = 'Creatinine Clearance'").fetchone()
    param = conn.execute(
        "SELECT id FROM test_parameters WHERE test_id = ?", (cc_test["id"],)
    ).fetchone()
    conn.execute("INSERT INTO patients (full_name, gender, age_years) VALUES ('P', 'Male', 40)")
    conn.execute(
        "INSERT INTO visits (patient_id, invoice_number, visit_date, total_amount) VALUES (1, 1, '2026-01-01', 0)"
    )
    conn.execute(
        "INSERT INTO visit_test_orders (visit_id, test_id, price, status) VALUES (1, ?, 0, 'Completed')",
        (cc_test["id"],),
    )
    conn.execute(
        "INSERT INTO result_values (visit_test_order_id, parameter_id, numeric_value, flag) "
        "VALUES (1, ?, 42.0, 'Normal')", (param["id"],),
    )
    conn.commit()
    conn.close()

    seed_if_empty()

    conn = db.get_connection()
    try:
        after = conn.execute(
            "SELECT name FROM test_parameters WHERE test_id = ?", (cc_test["id"],)
        ).fetchall()
        assert [r["name"] for r in after] == ["النتيجة"], "must not discard a real entered result"
        value = conn.execute(
            "SELECT numeric_value FROM result_values WHERE parameter_id = ?", (param["id"],)
        ).fetchone()
        assert value["numeric_value"] == 42.0
    finally:
        conn.close()


def test_backfill_additively_adds_missing_parameter_to_existing_breakdown(tmp_path, monkeypatch):
    """Simulates an install that already had the full CBC breakdown from before "Color Index" was
    added to profiles.json - the migration should append just that one missing parameter."""
    _init(tmp_path, monkeypatch)
    from app import seed as seed_module

    conn = db.get_connection()
    seed_module._seed_roles_and_admin(conn)
    test_ids = seed_module._seed_catalog(conn)
    profiles_data = seed_module._load("profiles.json")
    for entry in profiles_data["profiles"]:
        test_id = test_ids.get(entry.get("attachKey"))
        if test_id is None:
            continue
        params = [p for p in entry["parameters"] if p["name"] != "Color Index"]
        conn.execute("DELETE FROM test_parameters WHERE test_id = ?", (test_id,))
        for p in params:
            conn.execute(
                "INSERT INTO test_parameters (test_id, name, unit, data_type, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (test_id, p["name"], p.get("unit"), p.get("dataType", "Numeric"), p.get("displayOrder", 0)),
            )
    conn.commit()
    cbc_test_id = test_ids["cbc"]
    before = {r["name"] for r in conn.execute(
        "SELECT name FROM test_parameters WHERE test_id = ?", (cbc_test_id,)
    ).fetchall()}
    assert "Color Index" not in before
    conn.close()

    seed_if_empty()

    conn = db.get_connection()
    try:
        after = {r["name"] for r in conn.execute(
            "SELECT name FROM test_parameters WHERE test_id = ?", (cbc_test_id,)
        ).fetchall()}
        assert "Color Index" in after
        assert before <= after  # nothing pre-existing was removed
    finally:
        conn.close()
