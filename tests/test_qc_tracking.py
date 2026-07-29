"""Regression tests for internal QC tracking (target mean/SD, recorded values, Levey-Jennings
classification)."""
from app import db
from app.seed import seed_if_empty
from app.services import catalog_service, qc_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def _first_parameter_id():
    tests = catalog_service.search_tests()
    for t in tests:
        details = catalog_service.get_test_with_details(t["id"])
        if details.get("parameters"):
            return details["parameters"][0]["id"]
    raise AssertionError("seed data must include at least one test with parameters")


def test_recording_without_a_target_fails(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    param_id = _first_parameter_id()
    ok, message = qc_service.record_qc_value(param_id, "Level 1", 10.0)
    assert ok is False


def test_save_target_then_record_in_control_value(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    param_id = _first_parameter_id()
    qc_service.save_qc_target(param_id, "Level 1", target_mean=10.0, target_sd=1.0)

    ok, message = qc_service.record_qc_value(param_id, "Level 1", 10.2)
    assert ok
    assert "ضمن" in message

    history = qc_service.get_qc_history(param_id, "Level 1")
    assert len(history) == 1
    assert history[0]["status"] == "InControl"


def test_out_of_control_value_is_flagged(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    param_id = _first_parameter_id()
    qc_service.save_qc_target(param_id, "Level 1", target_mean=10.0, target_sd=1.0)

    ok, message = qc_service.record_qc_value(param_id, "Level 1", 14.0)  # 4 SD away
    assert ok
    assert "السيطرة" in message

    history = qc_service.get_qc_history(param_id, "Level 1")
    assert history[-1]["status"] == "OutOfControl"


def test_saving_target_twice_updates_instead_of_duplicating(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    param_id = _first_parameter_id()
    qc_service.save_qc_target(param_id, "Level 1", target_mean=10.0, target_sd=1.0)
    qc_service.save_qc_target(param_id, "Level 1", target_mean=12.0, target_sd=2.0)

    target = qc_service.get_qc_target(param_id, "Level 1")
    assert target["target_mean"] == 12.0
    assert target["target_sd"] == 2.0
