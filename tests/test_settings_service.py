from app import db
from app.services import catalog_service


def test_get_settings_dashboard_data_includes_core_records(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "settings_laplis.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    data = catalog_service.get_settings_dashboard_data()

    assert data["lab_settings"]["lab_name"]
    assert data["departments"]
    assert data["referral_sources"]
    assert data["doctors"]


def test_brand_colors_saved_and_retrieved(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "brand_colors.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    settings = catalog_service.get_lab_settings()
    settings["brand_primary_color"] = "#0D9488"
    settings["brand_secondary_color"] = "#0F766E"
    catalog_service.save_lab_settings(settings)

    updated = catalog_service.get_lab_settings()
    assert updated["brand_primary_color"] == "#0D9488"
    assert updated["brand_secondary_color"] == "#0F766E"


def test_referral_and_doctor_updates_are_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "settings_laplis.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    source_id = catalog_service.save_referral_source("جهة جديدة")
    catalog_service.save_referral_source("جهة محدثة", source_id=source_id)
    doctor_id = catalog_service.save_doctor("د. جديد")
    catalog_service.save_doctor("د. محدث", doctor_id=doctor_id)

    sources = catalog_service.get_referral_sources()
    doctors = catalog_service.get_doctors()

    assert any(s["name"] == "جهة محدثة" for s in sources)
    assert any(d["full_name"] == "د. محدث" for d in doctors)


def test_deactivating_referral_and_doctor_hides_them(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "settings_laplis.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    source_id = catalog_service.save_referral_source("جهة مؤقتة")
    doctor_id = catalog_service.save_doctor("د. مؤقت")

    catalog_service.deactivate_referral_source(source_id)
    catalog_service.deactivate_doctor(doctor_id)

    sources = catalog_service.get_referral_sources()
    doctors = catalog_service.get_doctors()

    assert not any(s["id"] == source_id for s in sources)
    assert not any(d["id"] == doctor_id for d in doctors)


def test_seed_grants_settings_access_to_admin_role(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "settings_laplis.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    conn = db.get_connection()
    try:
        admin_role_id = conn.execute("SELECT id FROM roles WHERE name = ?", ("مدير النظام",)).fetchone()["id"]
        row = conn.execute(
            "SELECT can_view FROM role_permissions WHERE role_id = ? AND module_key = ?",
            (admin_role_id, "Settings"),
        ).fetchone()
        assert row is not None and row["can_view"] == 1
    finally:
        conn.close()


def test_catalog_dashboard_stats_count_active_and_inactive_tests(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "catalog_stats.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    conn = db.get_connection()
    try:
        test_id = conn.execute("SELECT id FROM tests ORDER BY id LIMIT 1").fetchone()["id"]
        conn.execute("UPDATE tests SET is_active = 0 WHERE id = ?", (test_id,))
        conn.commit()
    finally:
        conn.close()

    stats = catalog_service.get_catalog_dashboard_stats()

    assert stats["total_tests"] >= 1
    assert stats["active_tests"] >= 0
    assert stats["inactive_tests"] >= 1
    assert stats["total_departments"] >= 1
    assert stats["total_referral_sources"] >= 1
    assert stats["total_doctors"] >= 1


def test_catalog_export_import_round_trip(tmp_path, monkeypatch):
    """Export full catalog then re-import into fresh DB – all tests must round-trip cleanly."""
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "catalog_io.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    # --- Export ---
    export_path = str(tmp_path / "catalog_export.json")
    count, msg = catalog_service.export_catalog_to_json(export_path)
    assert count > 0, "Expected at least one test to be exported"
    import os
    assert os.path.isfile(export_path), "Export file was not created"

    # Read original test names
    original_tests = catalog_service.search_tests(include_inactive=True)
    original_names = {t["name"] for t in original_tests}

    # --- Wipe tests from DB and re-import ---
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM parameter_reference_ranges")
        conn.execute("DELETE FROM test_parameters")
        conn.execute("DELETE FROM price_list_items")
        conn.execute("DELETE FROM tests")
        conn.execute("DELETE FROM departments")
        conn.commit()
    finally:
        conn.close()

    added, updated, errors, msg2 = catalog_service.import_catalog_from_json(export_path)
    assert added == count, f"Expected {count} tests re-added, got {added}"
    assert updated == 0
    assert not errors, f"Unexpected errors during import: {errors}"

    reimported = catalog_service.search_tests(include_inactive=True)
    reimported_names = {t["name"] for t in reimported}
    assert original_names == reimported_names, "Re-imported test names do not match original"


def test_catalog_import_update_mode(tmp_path, monkeypatch):
    """Import in add_and_update mode should update existing tests without duplicating."""
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "catalog_update.db"))
    db.init_schema()
    from app.seed import seed_if_empty
    seed_if_empty()

    export_path = str(tmp_path / "cat_update.json")
    count, _ = catalog_service.export_catalog_to_json(export_path)

    # Re-import with add_and_update – all should be updated, none added
    added, updated, errors, msg = catalog_service.import_catalog_from_json(
        export_path, merge_mode="add_and_update"
    )
    assert added == 0
    assert updated == count
    assert not errors


def test_storage_root_config(tmp_path):
    """get_storage_root returns configured path after set_storage_root."""
    import app.config as cfg
    original_config = cfg._STORAGE_CONFIG_PATH

    # Point config file to a temp location
    cfg._STORAGE_CONFIG_PATH = str(tmp_path / "storage_config.json")
    try:
        new_root = str(tmp_path / "MyLapLIS")
        cfg.set_storage_root(new_root)
        assert cfg.get_storage_root() == new_root
        # Verify sub-directories were created
        import os
        assert os.path.isdir(cfg.get_pdf_reports_dir(new_root))
        assert os.path.isdir(cfg.get_exports_catalog_dir(new_root))
        assert os.path.isdir(cfg.get_backups_dir(new_root))
    finally:
        cfg._STORAGE_CONFIG_PATH = original_config

