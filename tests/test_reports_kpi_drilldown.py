"""Regression tests: Reports & Statistics KPI cards are clickable and drill down into the
individual visits behind the number, and the dashboard/reports detail dialog supports live search."""
from app import db
from app.seed import seed_if_empty
from app.services import auth_service, catalog_service, reports_service, visit_service


def _init(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_laplis.db"))
    db.init_schema()
    seed_if_empty()


def test_get_visits_in_range_returns_per_visit_rows_with_balance(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()

    visit_service.create_visit(
        patient={"full_name": "مريض أ", "gender": "Male", "age_years": 25},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=5, user_id=user.user_id,
    )

    visits = reports_service.get_visits_in_range()
    assert len(visits) == 1
    v = visits[0]
    assert v["patient_name"] == "مريض أ"
    assert v["balance"] == v["total_amount"] - v["discount_amount"] - v["paid_amount"]


def test_get_visits_in_range_only_outstanding_filters_fully_paid_visits(tmp_path, monkeypatch):
    _init(tmp_path, monkeypatch)
    user = auth_service.login("admin", "Admin@123")
    tests = catalog_service.search_tests()
    price = catalog_service.get_price(tests[0]["id"], "Individual")

    visit_service.create_visit(
        patient={"full_name": "مريض مسدد بالكامل", "gender": "Male", "age_years": 25},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=price, user_id=user.user_id,
    )
    visit_service.create_visit(
        patient={"full_name": "مريض متبقي عليه", "gender": "Male", "age_years": 25},
        doctor_id=None, referral_source_id=None, test_ids=[tests[0]["id"]],
        discount=0, initial_payment=0, user_id=user.user_id,
    )

    all_visits = reports_service.get_visits_in_range()
    assert len(all_visits) == 2

    outstanding = reports_service.get_visits_in_range(only_outstanding=True)
    assert len(outstanding) == 1
    assert outstanding[0]["patient_name"] == "مريض متبقي عليه"
