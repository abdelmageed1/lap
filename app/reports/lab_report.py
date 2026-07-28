"""Generates the printed lab-results report for a completed test order, as a right-to-left A4 PDF."""
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from reportlab.lib.colors import white as WHITE

from app.config import REPORTS_DIR
from app.reports.pdf_base import (BRAND_DARK, BRAND_GRAY, BRAND_RED, BRAND_TEAL, FONT_BOLD,
                                   draw_rtl_label_value, draw_rtl_text, ensure_fonts_registered)
from app.services.result_service import FLAG_LABELS

PAGE_W, PAGE_H = A4
MARGIN = 40
RIGHT = PAGE_W - MARGIN
LEFT = MARGIN


def _sanitize_filename(text: str) -> str:
    if not text:
        return "file"
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(ch, "_")
    return text.strip().replace(" ", "_")


def generate_lab_report_pdf(patient_name: str, gender: str, age_years, test_name: str,
                             parameters_with_values: list, lab_settings: dict, invoice_number: int) -> str:
    """parameters_with_values: list of dicts with name, unit, numeric_value/text_value, range_low/high/text, flag."""
    ensure_fonts_registered()
    safe_test = _sanitize_filename(test_name)
    safe_patient = _sanitize_filename(patient_name)
    filename = f"{safe_test}_{invoice_number}_{safe_patient}.pdf"
    path = os.path.join(REPORTS_DIR, filename)
    c = canvas.Canvas(path, pagesize=A4)


    y = PAGE_H - 50
    draw_rtl_text(c, RIGHT, y, lab_settings.get("lab_name") or "المعمل", font=FONT_BOLD, size=18, color=BRAND_DARK)
    y -= 20
    if lab_settings.get("tagline"):
        draw_rtl_text(c, RIGHT, y, lab_settings["tagline"], size=10, color=BRAND_GRAY)
        y -= 16

    c.setStrokeColor(BRAND_TEAL)
    y -= 4
    c.line(LEFT, y, RIGHT, y)
    y -= 22

    draw_rtl_label_value(c, RIGHT, y, "تقرير نتيجة", test_name, font=FONT_BOLD, size=13, color=BRAND_TEAL)
    y -= 18
    age_display = f"{age_years:.0f} سنة" if age_years is not None else "-"
    gender_display = "ذكر" if gender == "Male" else "أنثى"
    draw_rtl_label_value(c, RIGHT, y, "المريض", patient_name, size=10.5)
    draw_rtl_label_value(c, RIGHT - 200, y, "النوع", gender_display, size=10.5)
    draw_rtl_label_value(c, RIGHT - 320, y, "السن", age_display, size=10.5)
    y -= 24

    col_flag_right = RIGHT
    col_range_right = RIGHT - 90
    col_value_right = RIGHT - 220
    col_name_right = RIGHT - 320

    c.setFillColor(BRAND_TEAL)
    c.rect(LEFT, y - 4, RIGHT - LEFT, 20, fill=1, stroke=0)
    draw_rtl_text(c, col_name_right, y, "المعيار", font=FONT_BOLD, size=9.5, color=WHITE)
    draw_rtl_text(c, col_value_right, y, "القيمة", font=FONT_BOLD, size=9.5, color=WHITE)
    draw_rtl_text(c, col_range_right, y, "المدى الطبيعي", font=FONT_BOLD, size=9.5, color=WHITE)
    draw_rtl_text(c, col_flag_right, y, "الحالة", font=FONT_BOLD, size=9.5, color=WHITE)
    y -= 20

    for p in parameters_with_values:
        value_display = p.get("numeric_value")
        value_display = f"{value_display} {p.get('unit') or ''}".strip() if value_display is not None else (
            p.get("text_value") or "-")
        if p.get("range_low") is not None and p.get("range_high") is not None:
            range_display = f"{p['range_low']} - {p['range_high']}"
        else:
            range_display = p.get("range_text") or "-"

        flag = p.get("flag", "Normal")
        flag_color = BRAND_RED if flag in ("High", "Low", "Abnormal") else BRAND_DARK
        flag_display = FLAG_LABELS.get(flag, "طبيعي")

        draw_rtl_text(c, col_name_right, y, p["name"], size=9.5)
        draw_rtl_text(c, col_value_right, y, value_display, font=FONT_BOLD, size=9.5)
        draw_rtl_text(c, col_range_right, y, range_display, size=9, color=BRAND_GRAY)
        draw_rtl_text(c, col_flag_right, y, flag_display, size=9, color=flag_color)
        y -= 16
        if y < 100:
            c.showPage()
            y = PAGE_H - 60

    y -= 20
    c.setStrokeColor(BRAND_GRAY)
    c.line(LEFT, y, RIGHT, y)
    y -= 16
    sig1 = lab_settings.get("footer_signature1") or "مدير المعمل / التوقيع الإلكتروني"
    sig2 = lab_settings.get("footer_signature2") or ""
    draw_rtl_text(c, RIGHT, y, f"توقيع واعتماد: {sig1}", font=FONT_BOLD, size=9.5, color=BRAND_DARK)
    if sig2:
        draw_rtl_text(c, LEFT + 160, y, f"المراجع: {sig2}", font=FONT_BOLD, size=9.5, color=BRAND_DARK)
    y -= 14
    seal_text = lab_settings.get("digital_seal_text") or "🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً."
    draw_rtl_text(c, RIGHT, y, seal_text, size=8, color=BRAND_GRAY)

    c.showPage()


    c.save()
    return path

