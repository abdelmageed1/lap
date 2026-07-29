"""Regression tests for splitting the lab name and supervising doctor's name into separate
lab_settings fields, independently controllable from Settings and shown as separate lines on the
invoice/lab report headers instead of one combined string."""
import sqlite3

from app import db
from app.seed import seed_if_empty
from app.services import catalog_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))


def test_fresh_seed_gives_separate_lab_name_and_doctor_name(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    db.init_schema()
    seed_if_empty()

    settings = catalog_service.get_lab_settings()
    assert settings["lab_name"] == "معمل نخبة"
    assert settings["supervising_doctor_name"] == "د. مصطفى الزناتي"
    assert settings["lab_name_font_size"] == 20


def test_save_lab_settings_persists_custom_lab_name_font_size(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    db.init_schema()
    seed_if_empty()

    settings = catalog_service.get_lab_settings()
    settings["lab_name_font_size"] = 30
    catalog_service.save_lab_settings(settings)

    updated = catalog_service.get_lab_settings()
    assert updated["lab_name_font_size"] == 30


def test_save_lab_settings_persists_supervising_doctor_name(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    db.init_schema()
    seed_if_empty()

    settings = catalog_service.get_lab_settings()
    settings["lab_name"] = "معمل جديد"
    settings["supervising_doctor_name"] = "د. سارة أحمد"
    catalog_service.save_lab_settings(settings, user_id=1)

    updated = catalog_service.get_lab_settings()
    assert updated["lab_name"] == "معمل جديد"
    assert updated["supervising_doctor_name"] == "د. سارة أحمد"


def test_migration_splits_combined_lab_name_on_existing_database(tmp_path, monkeypatch):
    """A database created before this round had a single combined lab_name field (e.g. "معمل نخبة
    للدكتور مصطفى الزناتي"). Upgrading must split it automatically so the lab owner doesn't have
    to retype anything, without ever needing a supervising_doctor_name column to have existed."""
    _init(tmp_path, monkeypatch)

    conn = sqlite3.connect(db.DATABASE_PATH)
    conn.execute(
        "CREATE TABLE lab_settings (id INTEGER PRIMARY KEY CHECK (id = 1), lab_name TEXT NOT NULL, "
        "tagline TEXT, address TEXT, phone_numbers TEXT, footer_signature1 TEXT, footer_signature2 TEXT)"
    )
    conn.execute(
        "INSERT INTO lab_settings (id, lab_name, tagline) VALUES (1, ?, ?)",
        ("معمل نخبة للدكتور مصطفى الزناتي", "معملك الطبي الموثوق"),
    )
    conn.commit()
    conn.close()

    db.init_schema()

    settings = catalog_service.get_lab_settings()
    assert settings["lab_name"] == "معمل نخبة"
    assert settings["supervising_doctor_name"] == "د. مصطفى الزناتي"
    assert settings["tagline"] == "معملك الطبي الموثوق"  # untouched


def test_migration_leaves_unrecognized_lab_name_pattern_untouched(tmp_path, monkeypatch):
    """If the old combined name doesn't match the known "للدكتور" pattern, don't guess - just add
    the new column empty and let the lab owner fill it in from Settings."""
    _init(tmp_path, monkeypatch)

    conn = sqlite3.connect(db.DATABASE_PATH)
    conn.execute(
        "CREATE TABLE lab_settings (id INTEGER PRIMARY KEY CHECK (id = 1), lab_name TEXT NOT NULL, "
        "tagline TEXT, address TEXT, phone_numbers TEXT, footer_signature1 TEXT, footer_signature2 TEXT)"
    )
    conn.execute("INSERT INTO lab_settings (id, lab_name) VALUES (1, 'Some Custom Lab Name')")
    conn.commit()
    conn.close()

    db.init_schema()

    settings = catalog_service.get_lab_settings()
    assert settings["lab_name"] == "Some Custom Lab Name"
    assert not settings.get("supervising_doctor_name")


def test_running_migration_twice_does_not_re_split_an_already_split_name(tmp_path, monkeypatch):
    """The auto-split must only ever run once (guarded by column-not-existing-yet), so a lab that
    deliberately keeps "للدكتور" in its lab_name after the first migration is never re-split."""
    _init(tmp_path, monkeypatch)
    db.init_schema()
    seed_if_empty()

    settings = catalog_service.get_lab_settings()
    settings["lab_name"] = "معمل نخبة للدكتور آخر"
    catalog_service.save_lab_settings(settings)

    db.init_schema()  # re-running init_schema (e.g. on every app startup) must be a no-op here

    after = catalog_service.get_lab_settings()
    assert after["lab_name"] == "معمل نخبة للدكتور آخر"
