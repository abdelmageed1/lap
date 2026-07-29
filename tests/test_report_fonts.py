"""Guards the printed-document font choice (invoices, lab result reports).

This codebase has no HarfBuzz/OpenType-shaping engine: app/reports/arabic_text.shape() (via
arabic_reshaper + python-bidi) maps Arabic text directly to literal Arabic Presentation Forms-B
codepoints (U+FE70-FEFF), which must exist in the registered font's cmap or those letters render
as blank ".notdef" boxes. Several modern Arabic webfonts (verified during this round: Tajawal,
Almarai) only support shaping through OpenType GSUB features and are missing some of those
codepoints outright - a silent, easy-to-miss regression if the report font is ever swapped again.
"""
import os

import arabic_reshaper
from reportlab.pdfbase.ttfonts import TTFont

from app.reports.pdf_base import FONT_BOLD_FILE, FONT_DIR, FONT_REGULAR_FILE, ensure_fonts_registered
from app.reports import pdf_base


def _missing_codepoints(font_path, texts):
    face = TTFont("CheckFont", font_path).face
    missing = set()
    for text in texts:
        reshaped = arabic_reshaper.reshape(text)
        for ch in reshaped:
            if ord(ch) not in face.charToGlyph:
                missing.add(ch)
    return missing


SAMPLE_TEXTS = [
    "معمل نخبة للدكتور مصطفى الزناتي",
    "تقرير نتيجة تحليل: صورة دم كاملة",
    "اسم المريض السن النوع المدى الطبيعي الحالة",
    "مرتفع منخفض طبيعي غير طبيعي",
    "فاتورة مدفوعة رقم الفاتورة تاريخ الإصدار الطبيب المحول جهة الإحالة",
    "الإجمالي الخصم المدفوع المتبقي جنيه مصري",
]


def test_registered_regular_font_has_full_arabic_presentation_forms_coverage():
    path = os.path.join(FONT_DIR, FONT_REGULAR_FILE)
    missing = _missing_codepoints(path, SAMPLE_TEXTS)
    assert not missing, f"font is missing glyphs for: {[hex(ord(c)) for c in missing]}"


def test_registered_bold_font_has_full_arabic_presentation_forms_coverage():
    path = os.path.join(FONT_DIR, FONT_BOLD_FILE)
    missing = _missing_codepoints(path, SAMPLE_TEXTS)
    assert not missing, f"font is missing glyphs for: {[hex(ord(c)) for c in missing]}"


def test_registered_fonts_have_full_latin_and_digit_coverage():
    """Test names/units mix English abbreviations (CBC, WBC, g/dL...) with Arabic labels."""
    for font_file in (FONT_REGULAR_FILE, FONT_BOLD_FILE):
        face = TTFont("CheckFont", os.path.join(FONT_DIR, font_file)).face
        missing = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789./%-"
                   if ord(c) not in face.charToGlyph]
        assert not missing, f"{font_file} is missing Latin/digit glyphs: {missing}"


def test_ensure_fonts_registered_is_idempotent():
    pdf_base._registered = False
    ensure_fonts_registered()
    ensure_fonts_registered()  # must not raise on double-registration
