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
