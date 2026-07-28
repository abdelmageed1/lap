from app import db
from app.services import catalog_service, reports_service, visit_service


def test_reports_service(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "test_reports.db"))
    db.init_schema()

    from app.seed import seed_if_empty
    seed_if_empty()

    # Create doctor and referral source
    doc_id = catalog_service.save_doctor("دكتور أحمد الشريف")
    source_id = catalog_service.save_referral_source("شركة التأمين A")

    # Create visit
    patient = {"full_name": "محمود سمير", "phone": "01000000001", "gender": "Male", "age_years": 35}
    tests = catalog_service.search_tests("")
    test_id = tests[0]["id"] if tests else 1


    visit = visit_service.create_visit(
        patient=patient,
        doctor_id=doc_id,
        referral_source_id=source_id,
        test_ids=[test_id],
        discount=10.0,
        initial_payment=50.0,
    )
    assert visit["invoice_number"] is not None

    # 1. Test top referring doctors
    top_docs = reports_service.get_top_referring_doctors()
    assert len(top_docs) >= 1
    target_doc = next((d for d in top_docs if d["doctor_id"] == doc_id), None)
    assert target_doc is not None
    assert target_doc["doctor_name"] == "دكتور أحمد الشريف"
    assert target_doc["visit_count"] == 1

    # 2. Test doctor patients drilldown
    drilldown = reports_service.get_doctor_patients_drilldown(doc_id)
    assert len(drilldown) == 1
    assert drilldown[0]["patient_name"] == "محمود سمير"
    assert drilldown[0]["invoice_number"] == visit["invoice_number"]

    # 3. Test referral sources analytics
    sources = reports_service.get_referral_sources_analytics()
    assert len(sources) >= 1

    # 4. Test department revenue breakdown
    deps = reports_service.get_department_revenue_breakdown()
    assert isinstance(deps, list)

    # 5. Test staff productivity analytics
    staff_analytics = reports_service.get_staff_productivity_analytics()
    assert isinstance(staff_analytics, list)
    if staff_analytics:
        admin_user = staff_analytics[0]
        staff_drilldown = reports_service.get_staff_activity_drilldown(admin_user["user_id"])
        assert isinstance(staff_drilldown, list)

