"""Generates the visit invoice as a right-to-left A4 PDF."""
import os
from datetime import datetime

from reportlab.lib.colors import white as WHITE
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.config import INVOICES_DIR
from app.reports.pdf_base import (BRAND_DARK, BRAND_GRAY, BRAND_RED, BRAND_TEAL, FONT_BOLD, FONT_REGULAR,
                                   draw_rtl_label_value, draw_rtl_text, ensure_fonts_registered)

PAGE_W, PAGE_H = A4
MARGIN = 40
RIGHT = PAGE_W - MARGIN
LEFT = MARGIN


def generate_invoice_pdf(visit: dict, orders: list, lab_settings: dict) -> str:
    ensure_fonts_registered()
    path = os.path.join(INVOICES_DIR, f"invoice-{visit['invoice_number']}.pdf")
    c = canvas.Canvas(path, pagesize=A4)

    y = PAGE_H - 50
    draw_rtl_text(c, RIGHT, y, lab_settings.get("lab_name") or "المعمل", font=FONT_BOLD, size=20, color=BRAND_DARK)
    y -= 22
    if lab_settings.get("tagline"):
        draw_rtl_text(c, RIGHT, y, lab_settings["tagline"], size=11, color=BRAND_GRAY)
        y -= 16
    if lab_settings.get("address"):
        draw_rtl_text(c, RIGHT, y, lab_settings["address"], size=9, color=BRAND_GRAY)
        y -= 13
    if lab_settings.get("phone_numbers"):
        draw_rtl_text(c, RIGHT, y, lab_settings["phone_numbers"], size=9, color=BRAND_GRAY)
        y -= 13

    c.setStrokeColor(BRAND_TEAL)
    c.setLineWidth(1.2)
    y -= 6
    c.line(LEFT, y, RIGHT, y)
    y -= 26

    draw_rtl_text(c, RIGHT, y, f"فاتورة رقم {visit['invoice_number']}", font=FONT_BOLD, size=14, color=BRAND_TEAL)
    y -= 20

    info_lines = [("المريض", visit["patient_name"]),
                  ("التاريخ", datetime.fromisoformat(visit["visit_date"]).strftime("%Y/%m/%d %H:%M"))]
    if visit.get("doctor_name"):
        info_lines.append(("الطبيب المحوِّل", visit["doctor_name"]))
    if visit.get("source_name"):
        info_lines.append(("جهة الإحالة", visit["source_name"]))

    for label, value in info_lines:
        draw_rtl_label_value(c, RIGHT, y, label, value, size=10.5)
        y -= 15

    y -= 10
    # Table header (RTL columns: test name first/right-most, price second)
    col_name_right = RIGHT
    col_price_right = RIGHT - 320
    c.setFillColor(BRAND_TEAL)
    c.rect(LEFT, y - 4, RIGHT - LEFT, 20, fill=1, stroke=0)
    draw_rtl_text(c, col_name_right, y, "التحليل", font=FONT_BOLD, size=10, color=WHITE)
    draw_rtl_text(c, col_price_right, y, "السعر", font=FONT_BOLD, size=10, color=WHITE)
    y -= 22

    for o in orders:
        draw_rtl_text(c, col_name_right, y, o["test_name"], size=10)
        draw_rtl_text(c, col_price_right, y, f"{o['price']:.2f}", size=10)
        y -= 16
        if y < 120:
            c.showPage()
            y = PAGE_H - 60

    y -= 8
    c.setStrokeColor(BRAND_GRAY)
    c.line(LEFT, y, RIGHT, y)
    y -= 20

    totals = [
        ("الإجمالي", visit["total_amount"], BRAND_DARK),
        ("الخصم", visit["discount_amount"], BRAND_GRAY),
        ("المدفوع", visit["paid_amount"], BRAND_TEAL),
        ("المتبقي", visit["balance"], BRAND_RED),
    ]
    for label, value, color in totals:
        draw_rtl_label_value(c, RIGHT, y, label, f"{value:.2f}", font=FONT_BOLD, size=11, color=color)
        y -= 17

    c.showPage()
    c.save()
    return path
