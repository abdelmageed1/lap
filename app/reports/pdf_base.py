"""Shared ReportLab setup: registers the bundled Arabic font and provides small RTL drawing helpers."""
import os

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.reports.arabic_text import shape

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_REGULAR = "Amiri"
FONT_BOLD = "Amiri-Bold"
FONT_REGULAR_FILE = "Amiri-Regular.ttf"
FONT_BOLD_FILE = "Amiri-Bold.ttf"

_registered = False


def ensure_fonts_registered() -> None:
    """Amiri (a Naskh-style Arabic typeface modeled on classic Bulaq Press typesetting, SIL OFL
    licensed) is used for every printed document - invoices and lab result reports are official
    paperwork handed to patients, and Amiri gives them the formal, typeset look that a generic
    sans-serif font like the previously-used DejaVu Sans does not.

    Font choice constraint - do not swap this for another Arabic webfont (Cairo/Tajawal/Almarai/
    etc.) without checking coverage first: this codebase has no HarfBuzz/OpenType-shaping engine,
    so `arabic_text.shape()` (arabic_reshaper + python-bidi) maps text to literal Arabic
    Presentation Forms-B codepoints (U+FE70-FEFF) that must exist directly in the font's cmap.
    Many modern Arabic webfonts (verified: Tajawal, Almarai) only support shaping via OpenType
    GSUB features and are missing several presentation-form codepoints outright - text drawn with
    them silently shows blank ".notdef" boxes for certain letter/position combinations (e.g. isolated
    alef/reh). Amiri and IBM Plex Sans Arabic were verified to have complete presentation-forms
    coverage plus full Latin coverage (needed since test names/units mix English abbreviations with
    Arabic labels) - see tests/test_report_fonts.py, which guards against a future regression.
    """
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, os.path.join(FONT_DIR, FONT_REGULAR_FILE)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(FONT_DIR, FONT_BOLD_FILE)))
    _registered = True


BRAND_DARK = HexColor("#0B4F6C")
BRAND_TEAL = HexColor("#146C8E")
BRAND_GRAY = HexColor("#64748B")
BRAND_LIGHT_BG = HexColor("#F8FAFC")
BRAND_BORDER = HexColor("#E2E8F0")
BRAND_RED = HexColor("#DC2626")
BRAND_GREEN = HexColor("#166534")
BRAND_BLACK = HexColor("#1E293B")


def draw_logo(c, x, y, width=65, height=65, logo_override_path=None) -> bool:
    """Draw lab logo dynamically with aspect ratio preserved. Returns True if logo was drawn."""
    from app.config import get_logo_png_path, get_logo_path
    path = logo_override_path or get_logo_png_path() or get_logo_path()
    if path and os.path.exists(path):
        try:
            # ReportLab supports PNG, JPEG, GIF directly. If SVG, try or fallback gracefully.
            if path.lower().endswith(".svg"):
                # Try Qt conversion if available
                png_path = get_logo_png_path()
                if png_path and os.path.exists(png_path) and not png_path.lower().endswith(".svg"):
                    path = png_path
            c.drawImage(path, x, y, width=width, height=height, preserveAspectRatio=True, mask='auto')
            return True
        except Exception:
            pass
    return False


def draw_card_box(c, x, y, width, height, bg_color=BRAND_LIGHT_BG, border_color=BRAND_BORDER, radius=6):
    """Draw a smooth rounded card frame as a background container."""
    c.saveState()
    if bg_color:
        c.setFillColor(bg_color)
    if border_color:
        c.setStrokeColor(border_color)
        c.setLineWidth(0.8)
    else:
        c.setLineWidth(0)
    c.roundRect(x, y, width, height, radius, fill=1 if bg_color else 0, stroke=1 if border_color else 0)
    c.restoreState()


def draw_rtl_text(c, x_right, y, text, font=FONT_REGULAR, size=11, color=None):
    """Draws Arabic text right-aligned at x_right."""
    ensure_fonts_registered()
    c.setFont(font, size)
    c.setFillColor(color if color is not None else BRAND_BLACK)
    c.drawRightString(x_right, y, shape(text))


def draw_ltr_text(c, x_left, y, text, font=FONT_REGULAR, size=11, color=None):
    """Draws LTR (English/numbers) text left-aligned at x_left."""
    ensure_fonts_registered()
    c.setFont(font, size)
    c.setFillColor(color if color is not None else BRAND_BLACK)
    c.drawString(x_left, y, str(text) if text is not None else "")


def draw_centered_text(c, x_center, y, text, font=FONT_REGULAR, size=11, color=None):
    """Draws centered Arabic/LTR text at x_center."""
    ensure_fonts_registered()
    c.setFont(font, size)
    c.setFillColor(color if color is not None else BRAND_BLACK)
    c.drawCentredString(x_center, y, shape(text))


def draw_stamp_and_signature(c, x_right, y, lab_settings) -> int:
    """Draw doctor signature and digital stamp images dynamically if configured. Returns height consumed."""
    height_consumed = 0
    show_sig = bool(lab_settings.get("pdf_show_doctor_signature", 1))
    sig_path = lab_settings.get("pdf_doctor_signature_path", "")
    sig_title = lab_settings.get("pdf_doctor_signature_title") or "طبيب التحاليل المسؤول"

    show_stamp = bool(lab_settings.get("pdf_show_stamp", 1))
    stamp_path = lab_settings.get("pdf_stamp_path", "")

    # Draw stamp on the left side if available
    if show_stamp and stamp_path and os.path.exists(stamp_path):
        try:
            c.drawImage(stamp_path, x_right - 460, y - 45, width=65, height=65, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Draw signature image on the right side if available
    if show_sig:
        if sig_path and os.path.exists(sig_path):
            try:
                c.drawImage(sig_path, x_right - 100, y - 35, width=90, height=45, preserveAspectRatio=True, mask='auto')
                y -= 48
                height_consumed += 48
            except Exception:
                pass
        draw_rtl_text(c, x_right, y, f"اعتماد: {sig_title}", font=FONT_BOLD, size=9.5, color=BRAND_DARK)
        if lab_settings.get("supervising_doctor_name"):
            draw_rtl_text(c, x_right, y - 14, str(lab_settings["supervising_doctor_name"]), font=FONT_REGULAR, size=9, color=BRAND_GRAY)
            height_consumed += 14
        height_consumed += 16
    return height_consumed


def draw_rtl_label_value(c, x_right, y, label, value, font=FONT_REGULAR, size=10.5, color=None, gap=4):
    """Draws 'label: value' positioned right-to-left."""
    ensure_fonts_registered()
    c.setFont(font, size)
    c.setFillColor(color if color is not None else BRAND_BLACK)
    label_text = shape(f"{label}:") if label else ""
    c.drawRightString(x_right, y, label_text)
    label_width = c.stringWidth(label_text, font, size)
    value_text = shape(value)
    c.drawRightString(x_right - label_width - gap, y, value_text)

