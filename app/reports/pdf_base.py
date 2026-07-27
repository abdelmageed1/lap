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
BRAND_GRAY = HexColor("#6B7280")
BRAND_RED = HexColor("#C62828")


BRAND_BLACK = HexColor("#1A1A1A")


def draw_rtl_text(c, x_right, y, text, font=FONT_REGULAR, size=11, color=None):
    """Draws Arabic text right-aligned at x_right (the RTL equivalent of drawString).

    Always sets an explicit fill color (defaulting to near-black) rather than leaving whatever
    color a previous draw call left active on the canvas's shared graphics state.
    """
    ensure_fonts_registered()
    c.setFont(font, size)
    c.setFillColor(color if color is not None else BRAND_BLACK)
    c.drawRightString(x_right, y, shape(text))


def draw_rtl_label_value(c, x_right, y, label, value, font=FONT_REGULAR, size=11, color=None, gap=4):
    """Draws 'label: value' where value may contain digits/Latin text (dates, prices, English test
    names). Shaping+bidi-reordering a mixed Arabic/Latin/digit string as one run scrambles the
    Latin/numeric part, so the label and value are shaped/drawn separately and positioned by hand
    (label right-most, value to its left) to match natural RTL reading order.
    """
    ensure_fonts_registered()
    c.setFont(font, size)
    c.setFillColor(color if color is not None else BRAND_BLACK)
    label_text = shape(f"{label}:") if label else ""
    c.drawRightString(x_right, y, label_text)
    label_width = c.stringWidth(label_text, font, size)
    # Shaping a mono-directional string (pure Arabic, or pure digits/Latin) on its own is safe -
    # the scrambling only happens when Arabic and Latin/digit runs are reshaped together as one string.
    value_text = shape(value)
    c.drawRightString(x_right - label_width - gap, y, value_text)
