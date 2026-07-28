import os
import sys

from app.reports.invoice_report import generate_invoice_pdf
from app.reports.lab_report import generate_lab_report_pdf

visit = {
    "invoice_number": 1001,
    "patient_name": "أحمد محمد علي",
    "visit_date": "2026-07-28T20:00:00",
    "doctor_name": "د. مصطفى الزناتي",
    "source_name": "عيادة خارجية",
    "total_amount": 250.0,
    "discount_amount": 20.0,
    "paid_amount": 230.0,
    "balance": 0.0,
}

orders = [
    {"test_name": "صورة دم كاملة CBC", "price": 150.0},
    {"test_name": "تحليل سكر صائم Glucose", "price": 100.0},
]

settings = {
    "lab_name": "معمل نخبة للدكتور مصطفى الزناتي",
    "tagline": "معملك الطبي الموثوق",
    "address": "القاهرة - مصر",
    "phone_numbers": "01000000000",
}

try:
    inv_path = generate_invoice_pdf(visit, orders, settings)
    print("SUCCESS_INVOICE:", inv_path)
except Exception as e:
    import traceback
    traceback.print_exc()

params = [
    {"name": "Hemoglobin (Hb)", "numeric_value": 14.5, "unit": "g/dL", "range_low": 13.0, "range_high": 17.0, "flag": "Normal"},
    {"name": "WBCs Count", "numeric_value": 12.5, "unit": "x10^3/uL", "range_low": 4.0, "range_high": 11.0, "flag": "High"},
]

try:
    rep_path = generate_lab_report_pdf("أحمد محمد علي", "Male", 35, "صورة دم كاملة CBC", params, settings, 1001)
    print("SUCCESS_REPORT:", rep_path)
except Exception as e:
    import traceback
    traceback.print_exc()
