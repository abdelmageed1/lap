"""Regression tests for the automated weekly/monthly periodic report: due-date logic, report file
generation, and that check_and_run() persists periodic_report_last_sent without wiping other
lab_settings fields (a real risk since save_lab_settings() writes the whole row)."""
from datetime import date, timedelta

from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, periodic_report_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_is_report_due_false_when_disabled():
    assert periodic_report_service.is_report_due({"periodic_report_enabled": False}) is False


def test_is_report_due_true_when_never_sent():
    assert periodic_report_service.is_report_due({"periodic_report_enabled": True,
                                                    "periodic_report_last_sent": None}) is True


def test_is_report_due_respects_weekly_interval():
    settings = {"periodic_report_enabled": True, "periodic_report_frequency": "weekly"}
    today = date(2026, 7, 29)
    settings["periodic_report_last_sent"] = (today - timedelta(days=6)).isoformat()
    assert periodic_report_service.is_report_due(settings, today=today) is False
    settings["periodic_report_last_sent"] = (today - timedelta(days=7)).isoformat()
    assert periodic_report_service.is_report_due(settings, today=today) is True


def test_is_report_due_respects_monthly_interval():
    settings = {"periodic_report_enabled": True, "periodic_report_frequency": "monthly"}
    today = date(2026, 7, 29)
    settings["periodic_report_last_sent"] = (today - timedelta(days=20)).isoformat()
    assert periodic_report_service.is_report_due(settings, today=today) is False
    settings["periodic_report_last_sent"] = (today - timedelta(days=31)).isoformat()
    assert periodic_report_service.is_report_due(settings, today=today) is True


def test_generate_report_file_creates_an_xlsx(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr("app.services.periodic_report_service.get_periodic_reports_dir",
                        lambda: str(tmp_path / "periodic_reports"))
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    visit_service.create_visit(
        patient={"full_name": "مريض تقرير دوري", "gender": "Male", "age_years": 30},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=10, user_id=user.user_id,
    )

    settings = catalog_service.get_lab_settings()
    file_path = periodic_report_service.generate_report_file(settings)
    import os
    assert os.path.exists(file_path)


def test_check_and_run_updates_last_sent_without_wiping_other_settings(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    monkeypatch.setattr("app.services.periodic_report_service.get_periodic_reports_dir",
                        lambda: str(tmp_path / "periodic_reports"))

    settings = catalog_service.get_lab_settings()
    settings["periodic_report_enabled"] = True
    settings["periodic_report_frequency"] = "weekly"
    settings["lab_name"] = "معمل الاختبار الدوري"
    catalog_service.save_lab_settings(settings)

    result = periodic_report_service.check_and_run()
    assert result["ran"] is True
    assert result["emailed"] is False  # no SMTP configured

    updated = catalog_service.get_lab_settings()
    assert updated["periodic_report_last_sent"] == date.today().isoformat()
    assert updated["lab_name"] == "معمل الاختبار الدوري"  # unrelated field must survive


def test_check_and_run_is_a_noop_when_disabled(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    result = periodic_report_service.check_and_run()
    assert result["ran"] is False
