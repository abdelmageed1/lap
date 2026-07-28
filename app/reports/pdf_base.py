"""Shared ReportLab setup: registers the bundled Arabic font and provides small RTL drawing helpers."""
import os

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.reports.arabic_text import shape

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_REGULAR = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

_registered = False


def ensure_fonts_registered() -> None:
    """DejaVu Sans is used (rather than an Arabic-only Noto family font) because it is one of the
    few open, redistributable TTF files that ships glyphs for *both* Arabic presentation forms and
    the full Latin alphabet - this app's test names/dates/abbreviations are plain English mixed with
    Arabic labels, and Arabic-only fonts silently render Latin letters as blank glyphs.
    """
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, os.path.join(FONT_DIR, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
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

