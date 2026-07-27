"""Generates printable Code128 barcode labels, one per ordered test, for the sample tubes."""
import os

from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.config import REPORTS_DIR
from app.reports.pdf_base import BRAND_DARK, BRAND_GRAY, FONT_BOLD, draw_rtl_text, ensure_fonts_registered

PAGE_W, PAGE_H = A4
MARGIN = 20
LABEL_W = 250
LABEL_H = 110
GAP = 12
COLS = 2


def generate_sample_labels_pdf(patient_name: str, invoice_number: int, orders: list) -> str:
    """orders: list of {id, test_name, department_name}. One label per order, encoding
    "<invoice_number>-<order_id>" as the barcode value so a scanner can identify the exact
    sample/test at result-entry time."""
    ensure_fonts_registered()
    path = os.path.join(REPORTS_DIR, f"labels-{invoice_number}.pdf")
    c = canvas.Canvas(path, pagesize=A4)

    x = MARGIN
    y = PAGE_H - MARGIN - LABEL_H
    col = 0

    for order in orders:
        c.setStrokeColor(BRAND_GRAY)
        c.setLineWidth(0.6)
        c.rect(x, y, LABEL_W, LABEL_H, stroke=1, fill=0)

        text_right = x + LABEL_W - 8
        draw_rtl_text(c, text_right, y + LABEL_H - 18, patient_name, font=FONT_BOLD, size=10.5, color=BRAND_DARK)
        draw_rtl_text(c, text_right, y + LABEL_H - 34, order["test_name"], size=9.5)
        if order.get("department_name"):
            draw_rtl_text(c, text_right, y + LABEL_H - 48, order["department_name"], size=8, color=BRAND_GRAY)

        barcode_value = f"{invoice_number}-{order['id']}"
        drawing = createBarcodeDrawing(
            "Code128", value=barcode_value, barHeight=26, humanReadable=True, fontSize=8,
        )
        drawing.drawOn(c, x + (LABEL_W - drawing.width) / 2, y + 10)

        col += 1
        if col >= COLS:
            col = 0
            x = MARGIN
            y -= LABEL_H + GAP
        else:
            x += LABEL_W + GAP

        if y < MARGIN:
            c.showPage()
            x = MARGIN
            y = PAGE_H - MARGIN - LABEL_H
            col = 0

    c.showPage()
    c.save()
    return path
