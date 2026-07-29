"""Smoke tests for PDF generation: must not crash, must produce a real PDF, and (for the lab
report specifically) must not overlap the table header with the first data row - a real bug found
by rendering the PDF to an image during this round (see info/06-CHANGES-THIS-ROUND.md)."""
import os
import re

from app.reports.invoice_report import generate_invoice_pdf
from app.reports.lab_report import generate_lab_report_pdf


def _count_pdf_pages(path: str) -> int:
    """Counts real /Page objects (not the /Pages tree root) without needing a PDF-parsing
    dependency this app doesn't otherwise require."""
    with open(path, "rb") as f:
        data = f.read()
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def _sample_settings():
    return {
        "lab_name": "معمل نخبة للدكتور مصطفى الزناتي",
        "tagline": "معملك الطبي الموثوق",
        "address": "القاهرة - مصر",
        "phone_numbers": "01000000000",
    }


def test_generate_invoice_pdf_produces_a_real_file(tmp_path, monkeypatch):
    import app.reports.invoice_report as invoice_report
    monkeypatch.setattr(invoice_report, "INVOICES_DIR", str(tmp_path))

    visit = {
        "invoice_number": 9001, "patient_name": "مريض اختبار", "visit_date": "2026-01-01T10:00:00",
        "total_amount": 100.0, "discount_amount": 0.0, "paid_amount": 100.0, "balance": 0.0,
    }
    orders = [{"test_name": "CBC صورة دم كاملة", "price": 100.0}]
    path = generate_invoice_pdf(visit, orders, _sample_settings())
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000


def test_generate_lab_report_pdf_produces_a_real_file(tmp_path, monkeypatch):
    import app.reports.lab_report as lab_report
    monkeypatch.setattr(lab_report, "REPORTS_DIR", str(tmp_path))

    params = [
        {"name": "Hemoglobin (Hb)", "numeric_value": 14.5, "unit": "g/dL",
         "range_low": 13.0, "range_high": 17.0, "flag": "Normal"},
        {"name": "WBCs Count", "numeric_value": 12.5, "unit": "x10^3/uL",
         "range_low": 4.0, "range_high": 11.0, "flag": "High"},
    ]
    path = generate_lab_report_pdf("مريض اختبار", "Male", 35, "CBC صورة دم كاملة", params,
                                    _sample_settings(), 9001)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000


def test_lab_report_handles_many_parameters_across_multiple_pages(tmp_path, monkeypatch):
    """A 40-parameter report must span multiple PDF pages, and the column header must be
    redrawn on every page - not just the first (a real gap found and fixed this round)."""
    import app.reports.lab_report as lab_report
    monkeypatch.setattr(lab_report, "REPORTS_DIR", str(tmp_path))

    params = [
        {"name": f"معيار رقم {i}", "numeric_value": 10.0 + i, "unit": "unit",
         "range_low": 5.0, "range_high": 20.0, "flag": "Normal"}
        for i in range(40)
    ]
    path = generate_lab_report_pdf("مريض اختبار", "Male", 30, "تحليل طويل", params,
                                    _sample_settings(), 9002)
    assert os.path.exists(path)
    assert _count_pdf_pages(path) >= 2
