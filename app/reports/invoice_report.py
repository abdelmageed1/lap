"""Generates the visit invoice as a right-to-left A4 PDF with logo and professional styling."""
import os
from datetime import datetime

from reportlab.lib.colors import HexColor, white as WHITE
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.config import INVOICES_DIR
from app.reports.pdf_base import (BRAND_BLACK, BRAND_BORDER, BRAND_DARK, BRAND_GRAY, BRAND_GREEN,
                                   BRAND_LIGHT_BG, BRAND_RED, BRAND_TEAL, FONT_BOLD, FONT_REGULAR,
                                   draw_card_box, draw_centered_text, draw_logo, draw_rtl_label_value,
                                   draw_rtl_text, ensure_fonts_registered)

PAGE_W, PAGE_H = A4
MARGIN = 36
RIGHT = PAGE_W - MARGIN
LEFT = MARGIN
CONTENT_W = PAGE_W - (MARGIN * 2)
LOGO_WIDTH = 85
# The lab name is centered in the space to the right of the logo (not the full page width) so a
# long name never overlaps the logo, while still reading as "centered" in the available header area.
HEADER_TEXT_CENTER_X = (LEFT + LOGO_WIDTH + 15 + RIGHT) / 2


def generate_invoice_pdf(visit: dict, orders: list, lab_settings: dict) -> str:
    ensure_fonts_registered()
    path = os.path.join(INVOICES_DIR, f"invoice-{visit['invoice_number']}.pdf")
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

    invoice_number = visit.get('invoice_number', '-')
    invoice_title = lab_settings.get("invoice_title") or "فاتورة مدفوعة"
    draw_rtl_text(c, RIGHT, y, invoice_title, font=FONT_BOLD, size=16, color=brand_primary)
    draw_rtl_label_value(c, LEFT + 180, y, "رقم الفاتورة", f"#{invoice_number}", font=FONT_BOLD, size=11, color=BRAND_GRAY)
    y -= 20

    try:
        date_str = datetime.fromisoformat(visit["visit_date"]).strftime("%Y/%m/%d - %I:%M %p")
    except Exception:
        date_str = str(visit.get("visit_date", ""))

    card_h = 70 if visit.get("doctor_name") or visit.get("source_name") else 56
    draw_card_box(c, LEFT, y - card_h, CONTENT_W, card_h, bg_color=BRAND_LIGHT_BG, border_color=BRAND_BORDER, radius=8)
    card_y = y - 20

    draw_rtl_label_value(c, RIGHT - 12, card_y, "اسم المريض", visit.get("patient_name", "-"), font=FONT_BOLD, size=11, color=BRAND_BLACK)
    draw_rtl_label_value(c, RIGHT - 12, card_y - 18, "تاريخ الإصدار", date_str, font=FONT_REGULAR, size=10, color=BRAND_GRAY)
    draw_rtl_label_value(c, RIGHT - 12, card_y - 34, "وقت الإصدار", date_str.split(" - ")[-1] if " - " in date_str else date_str, font=FONT_REGULAR, size=10, color=BRAND_GRAY)

    if visit.get("doctor_name"):
        draw_rtl_label_value(c, RIGHT - 280, card_y, "الطبيب المحول", visit.get("doctor_name", "-"), size=10, color=BRAND_BLACK)
    if visit.get("source_name"):
        draw_rtl_label_value(c, RIGHT - 280, card_y - 18, "جهة الإحالة", visit.get("source_name", "-"), size=10, color=BRAND_BLACK)

    y = y - card_h - 28

    col_name_right = RIGHT - 15
    col_price_right = LEFT + 74

    # header_h is the header bar's own height; HEADER_GAP is extra clearance below it before the
    # first row's text baseline. This must exceed the font's ascent at the row font size, or glyph
    # tops visibly poke up into the header bar (a real, confirmed-by-rendering bug at the previous
    # header_h + 4 gap - see info/06-CHANGES-THIS-ROUND.md).
    header_h = 26
    HEADER_GAP = 12

    def draw_table_header(y_top):
        c.setFillColor(brand_primary)
        c.roundRect(LEFT, y_top - header_h + 4, CONTENT_W, header_h, 6, fill=1, stroke=0)
        draw_rtl_text(c, col_name_right, y_top - 12, "الخدمة أو التحليل", font=FONT_BOLD, size=10.5, color=WHITE)
        draw_rtl_text(c, col_price_right, y_top - 12, "السعر (ج.م)", font=FONT_BOLD, size=10.5, color=WHITE)
        return y_top - header_h - HEADER_GAP

    y = draw_table_header(y)

    row_h = 22
    for idx, order in enumerate(orders):
        if idx % 2 == 1:
            c.setFillColor(HexColor("#F7FAFC"))
            c.rect(LEFT, y - 4, CONTENT_W, row_h, fill=1, stroke=0)

        draw_rtl_text(c, col_name_right, y + 2, order.get("test_name", "-"), font=FONT_REGULAR, size=10, color=BRAND_BLACK)
        draw_rtl_text(c, col_price_right, y + 2, f"{order.get('price', 0.0):.2f}", font=FONT_BOLD, size=10, color=BRAND_BLACK)
        c.setStrokeColor(HexColor("#E2E8F0"))
        c.setLineWidth(0.5)
        c.line(LEFT, y - 4, RIGHT, y - 4)
        y -= row_h
        if y < 140:
            c.setFillColor(brand_primary)
            c.rect(0, PAGE_H - 8, PAGE_W, 8, fill=1, stroke=0)
            c.showPage()
            y = draw_table_header(PAGE_H - 60)

    y -= 18
    summary_w = 280
    summary_h = 78
    draw_card_box(c, LEFT, y - summary_h, summary_w, summary_h, bg_color=BRAND_LIGHT_BG, border_color=brand_secondary, radius=8)
    sum_y = y - 18
    sum_right = LEFT + summary_w - 12

    draw_rtl_label_value(c, sum_right, sum_y, "الإجمالي", f"{visit.get('total_amount', 0.0):.2f} ج.م", font=FONT_BOLD, size=10, color=BRAND_BLACK)
    draw_rtl_label_value(c, sum_right, sum_y - 18, "الخصم", f"{visit.get('discount_amount', 0.0):.2f} ج.م", font=FONT_REGULAR, size=10, color=BRAND_GRAY)
    draw_rtl_label_value(c, sum_right, sum_y - 36, "المدفوع", f"{visit.get('paid_amount', 0.0):.2f} ج.م", font=FONT_BOLD, size=10, color=BRAND_GREEN)
    bal_color = BRAND_RED if visit.get("balance", 0.0) > 0 else BRAND_DARK
    draw_rtl_label_value(c, sum_right, sum_y - 54, "المتبقي", f"{visit.get('balance', 0.0):.2f} ج.م", font=FONT_BOLD, size=10, color=bal_color)

    y = y - summary_h - 26
    c.setStrokeColor(BRAND_BORDER)
    c.setLineWidth(0.8)
    c.line(LEFT, y + 12, RIGHT, y + 12)

    footer_note = lab_settings.get("digital_seal_text") or "نشكركم لثقتكم بنا - الفاتورة معتمدة إلكترونياً وصادرة من النظام الآلي للمعمل."
    draw_rtl_text(c, RIGHT, y, footer_note, font=FONT_REGULAR, size=8.5, color=BRAND_GRAY)

    c.showPage()
    c.save()
    return path

