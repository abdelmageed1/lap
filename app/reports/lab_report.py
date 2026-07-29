"""Generates the printed lab-results report for a completed test order, as a right-to-left A4 PDF."""
import os

from reportlab.lib.colors import HexColor, white as WHITE
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.config import REPORTS_DIR
from app.reports.pdf_base import (BRAND_BLACK, BRAND_BORDER, BRAND_DARK, BRAND_GRAY, BRAND_GREEN,
                                   BRAND_LIGHT_BG, BRAND_RED, BRAND_TEAL, FONT_BOLD, FONT_REGULAR,
                                   draw_card_box, draw_centered_text, draw_logo, draw_rtl_label_value,
                                   draw_rtl_text, ensure_fonts_registered)
from app.services.result_service import FLAG_LABELS

PAGE_W, PAGE_H = A4
MARGIN = 36
RIGHT = PAGE_W - MARGIN
LEFT = MARGIN
CONTENT_W = PAGE_W - (MARGIN * 2)
LOGO_WIDTH = 85
# The lab name is centered in the space to the right of the logo (not the full page width) so a
# long name never overlaps the logo, while still reading as "centered" in the available header area.
HEADER_TEXT_CENTER_X = (LEFT + LOGO_WIDTH + 15 + RIGHT) / 2


def generate_lab_report_pdf(patient_name: str, gender: str, age_years, test_name: str,
                             parameters_with_values: list, lab_settings: dict, invoice_number: int) -> str:
    """parameters_with_values: list of dicts with name, unit, numeric_value/text_value, range_low/high/text, flag."""
    ensure_fonts_registered()
    safe_test = _sanitize_filename(test_name)
    safe_patient = _sanitize_filename(patient_name)
    filename = f"{safe_test}_{invoice_number}_{safe_patient}.pdf"
    path = os.path.join(REPORTS_DIR, filename)
    c = canvas.Canvas(path, pagesize=A4)

    primary_hex = lab_settings.get("brand_primary_color") or "#0B4F6C"
    secondary_hex = lab_settings.get("brand_secondary_color") or "#146C8E"
    try:
        brand_primary = HexColor(primary_hex)
    except Exception:
        brand_primary = BRAND_DARK
    try:
        brand_secondary = HexColor(secondary_hex)
    except Exception:
        brand_secondary = BRAND_TEAL

    c.setFillColor(brand_primary)
    c.rect(0, PAGE_H - 8, PAGE_W, 8, fill=1, stroke=0)

    y = PAGE_H - 45
    draw_logo(c, LEFT, y - 40, width=LOGO_WIDTH, height=60, logo_override_path=lab_settings.get("logo_path"))

    lab_name = lab_settings.get("lab_name") or "المعمل الطبي"
    lab_name_size = lab_settings.get("lab_name_font_size") or 20
    draw_centered_text(c, HEADER_TEXT_CENTER_X, y, lab_name, font=FONT_BOLD, size=lab_name_size, color=brand_primary)
    y -= round(lab_name_size * 1.2)

    if lab_settings.get("supervising_doctor_name"):
        draw_rtl_text(c, RIGHT, y, f"تحت إشراف {lab_settings['supervising_doctor_name']}",
                      font=FONT_BOLD, size=12, color=brand_secondary)
        y -= 18

    if lab_settings.get("tagline"):
        draw_rtl_text(c, RIGHT, y, lab_settings["tagline"], font=FONT_REGULAR, size=10.5, color=BRAND_GRAY)
        y -= 16

    contact_parts = []
    if lab_settings.get("address"):
        contact_parts.append(lab_settings["address"])
    if lab_settings.get("phone_numbers"):
        contact_parts.append(f"ت: {lab_settings['phone_numbers']}")
    if contact_parts:
        draw_rtl_text(c, RIGHT, y, " - ".join(contact_parts), font=FONT_REGULAR, size=9.5, color=BRAND_GRAY)
        y -= 16

    y -= 4
    c.setStrokeColor(BRAND_BORDER)
    c.setLineWidth(1)
    c.line(LEFT, y, RIGHT, y)
    y -= 22

    draw_rtl_text(c, RIGHT, y, f"تقرير نتيجة تحليل: {test_name}", font=FONT_BOLD, size=16, color=brand_primary)
    draw_rtl_label_value(c, LEFT + 140, y, "زيارة رقم", f"#{invoice_number}", font=FONT_BOLD, size=11, color=BRAND_GRAY)
    y -= 20

    age_display = f"{age_years:.0f} سنة" if age_years is not None else "-"
    gender_display = "ذكر" if gender == "Male" else ("أنثى" if gender == "Female" else (gender or "-"))

    draw_card_box(c, LEFT, y - 64, CONTENT_W, 64, bg_color=BRAND_LIGHT_BG, border_color=BRAND_BORDER, radius=8)
    card_y = y - 18
    draw_rtl_label_value(c, RIGHT - 12, card_y, "اسم المريض", patient_name, font=FONT_BOLD, size=11, color=BRAND_BLACK)
    draw_rtl_label_value(c, RIGHT - 12, card_y - 18, "السن", age_display, size=10, color=BRAND_BLACK)
    draw_rtl_label_value(c, RIGHT - 12, card_y - 36, "النوع", gender_display, size=10, color=BRAND_BLACK)

    y = y - 84

    col_name_right = RIGHT - 15
    col_value_right = RIGHT - 220
    col_range_right = RIGHT - 350
    col_flag_right = LEFT + 84

    # header_h is the header bar's own height; HEADER_GAP is extra clearance below it before the
    # first row's text baseline. This must exceed the font's ascent at the row font size, or glyph
    # tops visibly poke up into the header bar (a real, confirmed-by-rendering bug at the previous
    # header_h + 4 gap - see info/06-CHANGES-THIS-ROUND.md).
    header_h = 26
    HEADER_GAP = 12

    def draw_table_header(y_top):
        c.setFillColor(brand_primary)
        c.roundRect(LEFT, y_top - header_h + 4, CONTENT_W, header_h, 6, fill=1, stroke=0)
        draw_rtl_text(c, col_name_right, y_top - 12, "اسم المعيار", font=FONT_BOLD, size=10.5, color=WHITE)
        draw_rtl_text(c, col_value_right, y_top - 12, "القيمة", font=FONT_BOLD, size=10.5, color=WHITE)
        draw_rtl_text(c, col_range_right, y_top - 12, "المدى المرجعي", font=FONT_BOLD, size=10.5, color=WHITE)
        draw_rtl_text(c, col_flag_right, y_top - 12, "الحالة", font=FONT_BOLD, size=10.5, color=WHITE)
        return y_top - header_h - HEADER_GAP

    y = draw_table_header(y)

    row_h = 24
    for idx, p in enumerate(parameters_with_values):
        flag = p.get("flag", "Normal")
        is_abnormal = flag in ("High", "Low", "Abnormal")

        if is_abnormal:
            c.setFillColor(HexColor("#FEF2F2"))
            c.rect(LEFT, y - 4, CONTENT_W, row_h, fill=1, stroke=0)
        elif idx % 2 == 1:
            c.setFillColor(HexColor("#F8FAFC"))
            c.rect(LEFT, y - 4, CONTENT_W, row_h, fill=1, stroke=0)

        value_num = p.get("numeric_value")
        unit_str = f" {p.get('unit')}" if p.get("unit") else ""
        value_display = f"{value_num}{unit_str}".strip() if value_num is not None else (p.get("text_value") or "-")

        if p.get("range_low") is not None and p.get("range_high") is not None:
            range_display = f"{p['range_low']} - {p['range_high']}"
        else:
            range_display = p.get("range_text") or "-"

        flag_color = BRAND_RED if is_abnormal else BRAND_GREEN
        flag_display = FLAG_LABELS.get(flag, "طبيعي")

        draw_rtl_text(c, col_name_right, y + 4, p.get("name", "-"), font=FONT_REGULAR, size=10, color=BRAND_BLACK)
        draw_rtl_text(c, col_value_right, y + 4, value_display, font=FONT_BOLD if is_abnormal else FONT_REGULAR, size=10, color=flag_color if is_abnormal else BRAND_BLACK)
        draw_rtl_text(c, col_range_right, y + 4, range_display, font=FONT_REGULAR, size=9.5, color=BRAND_GRAY)
        draw_rtl_text(c, col_flag_right, y + 4, flag_display, font=FONT_BOLD if is_abnormal else FONT_REGULAR, size=9.5, color=flag_color)

        c.setStrokeColor(HexColor("#E2E8F0"))
        c.setLineWidth(0.5)
        c.line(LEFT, y - 4, RIGHT, y - 4)

        y -= row_h
        if y < 120:
            c.setFillColor(brand_primary)
            c.rect(0, PAGE_H - 8, PAGE_W, 8, fill=1, stroke=0)
            c.showPage()
            y = draw_table_header(PAGE_H - 60)

    y -= 28
    c.setStrokeColor(BRAND_BORDER)
    c.setLineWidth(0.8)
    c.line(LEFT, y + 12, RIGHT, y + 12)

    sig1 = lab_settings.get("footer_signature1") or "مدير المختبر"
    sig2 = lab_settings.get("footer_signature2") or "الطبيب المعتمد"
    draw_rtl_text(c, RIGHT, y - 4, f"توقيع واعتماد: {sig1}", font=FONT_BOLD, size=9.5, color=BRAND_DARK)
    draw_rtl_text(c, LEFT + 180, y - 4, f"المراجع: {sig2}", font=FONT_BOLD, size=9.5, color=BRAND_DARK)

    y -= 18
    seal_text = lab_settings.get("digital_seal_text") or "🔒 هذا التقرير مُعتمَد إلكترونيًا ولا يحتاج توقيعًا يدوياً."
    draw_rtl_text(c, RIGHT, y, seal_text, font=FONT_REGULAR, size=8.5, color=BRAND_GRAY)

    c.showPage()
    c.save()
    return path


def _sanitize_filename(text: str) -> str:
    if not text:
        return "file"
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(ch, "_")
    return text.strip().replace(" ", "_")

