"""PdfDesignerView: Interface for customizing PDF lab report and invoice layouts, paper mode,
margins, branding colors, doctor signature, stamp, and footer notes with preview.
"""
import os
import tempfile
from PySide2.QtCore import Qt
from PySide2.QtGui import QColor, QPixmap
from PySide2.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox,
                                 QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                                 QMessageBox, QPushButton, QRadioButton, QScrollArea,
                                 QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from app.reports.invoice_report import generate_invoice_pdf
from app.reports.lab_report import generate_lab_report_pdf
from app.services import catalog_service
from app.ui.animated_button import AnimatedButton


def _create_section_card(title_text: str) -> tuple[QFrame, QVBoxLayout]:
    """Create a styled section card with a clean section title to avoid QGroupBox title overlapping."""
    card = QFrame()
    card.setObjectName("Card")
    card.setStyleSheet("QFrame#Card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    title = QLabel(title_text)
    title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0B4F6C; margin-bottom: 4px;")
    layout.addWidget(title)
    return card, layout


class PdfDesignerView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------------
        # Left Panel: Controls Tabs
        # -------------------------------------------------------------------
        control_frame = QFrame()
        control_frame.setObjectName("Card")
        control_frame.setStyleSheet("QFrame#Card { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 10px; }")
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(16, 16, 16, 16)
        control_layout.setSpacing(12)

        header_title = QLabel("🎨 تصميم الـ PDF وإعدادات الطباعة")
        header_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0B4F6C; margin-bottom: 4px;")
        control_layout.addWidget(header_title)

        header_desc = QLabel("خصص نمط الورق، الهوامش، الشعار، الألوان، التوقيعات، والختم لتقارير المعمل والفواتير.")
        header_desc.setWordWrap(True)
        header_desc.setStyleSheet("font-size: 12px; color: #64748B; margin-bottom: 8px;")
        control_layout.addWidget(header_desc)

        self.tabs = QTabWidget()

        # ===================================================================
        # Tab 1: Paper & Margins
        # ===================================================================
        paper_scroll = QScrollArea()
        paper_scroll.setWidgetResizable(True)
        paper_scroll.setFrameShape(QScrollArea.NoFrame)
        paper_widget = QWidget()
        paper_layout = QVBoxLayout(paper_widget)
        paper_layout.setContentsMargins(8, 8, 8, 8)
        paper_layout.setSpacing(14)

        # Section 1: Paper Mode
        mode_card, mode_box = _create_section_card("📄 نمط الورق والطباعة (Paper Mode)")
        self.btn_white_paper = QRadioButton("طباعة كاملة على ورق أبيض فارغ (Full PDF Header & Footer)")
        self.btn_preprinted = QRadioButton("طباعة على ورق معنون جاهز (Pre-printed Letterhead - يترك مكان الهيدر فارغاً)")
        self.btn_white_paper.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B; padding: 4px;")
        self.btn_preprinted.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B; padding: 4px;")
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.btn_white_paper)
        self.mode_button_group.addButton(self.btn_preprinted)
        mode_box.addWidget(self.btn_white_paper)
        mode_box.addWidget(self.btn_preprinted)
        paper_layout.addWidget(mode_card)

        # Section 2: Paper Size
        size_card, size_box = _create_section_card("📐 مقاس الصفحة (Paper Size)")
        size_row = QHBoxLayout()
        lbl_size = QLabel("اختيار المقاس:")
        lbl_size.setStyleSheet("font-weight: bold; color: #334155;")
        self.combo_page_size = QComboBox()
        self.combo_page_size.addItems(["A4", "A5", "Thermal80 (80mm)"])
        size_row.addWidget(lbl_size)
        size_row.addWidget(self.combo_page_size, 1)
        size_box.addLayout(size_row)
        paper_layout.addWidget(size_card)

        # Section 3: Margins in mm
        margins_card, margins_box = _create_section_card("📏 أبعاد الهوامش بالمليمتر (Margins in mm)")
        
        m_grid = QVBoxLayout()
        m_grid.setSpacing(10)

        # Top Margin
        row_top = QHBoxLayout()
        lbl_top = QLabel("الهامش العلوي (Top Margin):")
        lbl_top.setMinimumWidth(170)
        self.spin_top_margin = QDoubleSpinBox()
        self.spin_top_margin.setRange(0, 150)
        self.spin_top_margin.setSuffix(" mm")
        row_top.addWidget(lbl_top)
        row_top.addWidget(self.spin_top_margin, 1)
        m_grid.addLayout(row_top)

        # Bottom Margin
        row_bottom = QHBoxLayout()
        lbl_bottom = QLabel("الهامش السفلي (Bottom Margin):")
        lbl_bottom.setMinimumWidth(170)
        self.spin_bottom_margin = QDoubleSpinBox()
        self.spin_bottom_margin.setRange(0, 150)
        self.spin_bottom_margin.setSuffix(" mm")
        row_bottom.addWidget(lbl_bottom)
        row_bottom.addWidget(self.spin_bottom_margin, 1)
        m_grid.addLayout(row_bottom)

        # Right & Left Margins
        row_sides = QHBoxLayout()
        lbl_right = QLabel("الهامش الأيمن:")
        self.spin_right_margin = QDoubleSpinBox()
        self.spin_right_margin.setRange(0, 100)
        self.spin_right_margin.setSuffix(" mm")

        lbl_left = QLabel("الهامش الأيسر:")
        self.spin_left_margin = QDoubleSpinBox()
        self.spin_left_margin.setRange(0, 100)
        self.spin_left_margin.setSuffix(" mm")

        row_sides.addWidget(lbl_right)
        row_sides.addWidget(self.spin_right_margin, 1)
        row_sides.addWidget(lbl_left)
        row_sides.addWidget(self.spin_left_margin, 1)
        m_grid.addLayout(row_sides)

        margins_box.addLayout(m_grid)
        paper_layout.addWidget(margins_card)

        paper_layout.addStretch()
        paper_scroll.setWidget(paper_widget)
        self.tabs.addTab(paper_scroll, "📄 الورق والهوامش")

        # ===================================================================
        # Tab 2: Branding & Signatures
        # ===================================================================
        brand_scroll = QScrollArea()
        brand_scroll.setWidgetResizable(True)
        brand_scroll.setFrameShape(QScrollArea.NoFrame)
        brand_widget = QWidget()
        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.setContentsMargins(8, 8, 8, 8)
        brand_layout.setSpacing(14)

        # Section 1: Colors
        color_card, color_box = _create_section_card("🎨 ألوان الهوية البصرية")
        color_row = QHBoxLayout()
        lbl_color = QLabel("اللون الرئيسي للتقرير:")
        lbl_color.setStyleSheet("font-weight: bold; color: #334155;")
        self.txt_primary_color = QLineEdit("#0B4F6C")
        self.txt_primary_color.setFixedWidth(100)
        self.btn_color_picker = QPushButton("🎨 اختيار لون")
        self.btn_color_picker.clicked.connect(self._pick_color)
        color_row.addWidget(lbl_color)
        color_row.addWidget(self.txt_primary_color)
        color_row.addWidget(self.btn_color_picker)
        color_row.addStretch()
        color_box.addLayout(color_row)
        brand_layout.addWidget(color_card)

        # Section 2: Logo
        logo_card, logo_box = _create_section_card("🖼️ الشعار (Logo) في الهيدر")
        self.chk_show_logo = QCheckBox("إظهار الشعار الرسمي في رأس الصفحة")
        self.chk_show_logo.setStyleSheet("font-weight: bold;")
        align_row = QHBoxLayout()
        lbl_align = QLabel("تموضع الشعار:")
        self.combo_logo_align = QComboBox()
        self.combo_logo_align.addItem("يمين الصفحة (Right)", "right")
        self.combo_logo_align.addItem("منتصف الصفحة (Center)", "center")
        self.combo_logo_align.addItem("يسار الصفحة (Left)", "left")
        align_row.addWidget(lbl_align)
        align_row.addWidget(self.combo_logo_align, 1)
        logo_box.addWidget(self.chk_show_logo)
        logo_box.addLayout(align_row)
        brand_layout.addWidget(logo_card)

        # Section 3: Signature & Stamp
        sig_card, sig_box = _create_section_card("✍️ التوقيع والختم الرقمي")
        
        self.chk_show_signature = QCheckBox("إظهار توقيع واعتماد الطبيب في التقرير")
        self.chk_show_signature.setStyleSheet("font-weight: bold;")
        sig_title_row = QHBoxLayout()
        lbl_sig_title = QLabel("مسمى التوقيع:")
        self.txt_sig_title = QLineEdit("طبيب التحاليل المسؤول")
        sig_title_row.addWidget(lbl_sig_title)
        sig_title_row.addWidget(self.txt_sig_title, 1)
        sig_box.addWidget(self.chk_show_signature)
        sig_box.addLayout(sig_title_row)

        sig_file_row = QHBoxLayout()
        self.txt_sig_path = QLineEdit()
        self.txt_sig_path.setReadOnly(True)
        self.txt_sig_path.setPlaceholderText("مسار صورة التوقيع...")
        btn_browse_sig = QPushButton("📁 رفع توقيع (PNG)")
        btn_browse_sig.clicked.connect(self._browse_signature)
        sig_file_row.addWidget(self.txt_sig_path, 1)
        sig_file_row.addWidget(btn_browse_sig)
        sig_box.addLayout(sig_file_row)

        stamp_file_row = QHBoxLayout()
        self.chk_show_stamp = QCheckBox("إظهار ختم المعمل الرقمي")
        self.chk_show_stamp.setStyleSheet("font-weight: bold;")
        self.txt_stamp_path = QLineEdit()
        self.txt_stamp_path.setReadOnly(True)
        self.txt_stamp_path.setPlaceholderText("مسار صورة الختم...")
        btn_browse_stamp = QPushButton("📁 رفع ختم (PNG)")
        btn_browse_stamp.clicked.connect(self._browse_stamp)
        stamp_file_row.addWidget(self.chk_show_stamp)
        stamp_file_row.addWidget(self.txt_stamp_path, 1)
        stamp_file_row.addWidget(btn_browse_stamp)
        sig_box.addLayout(stamp_file_row)

        brand_layout.addWidget(sig_card)
        brand_layout.addStretch()
        brand_scroll.setWidget(brand_widget)
        self.tabs.addTab(brand_scroll, "🎨 الألوان والتوقيعات")

        # ===================================================================
        # Tab 3: Header & Footer Text
        # ===================================================================
        text_scroll = QScrollArea()
        text_scroll.setWidgetResizable(True)
        text_scroll.setFrameShape(QScrollArea.NoFrame)
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(8, 8, 8, 8)
        text_layout.setSpacing(14)

        text_card, text_box = _create_section_card("📝 نصوص الهيدر والفوتر")

        text_box.addWidget(QLabel("اسم المعمل الرسمي (يظهر بالخط العريض أعلى التقرير):"))
        self.txt_lab_name = QLineEdit()
        text_box.addWidget(self.txt_lab_name)

        text_box.addWidget(QLabel("اسم الطبيب المشرف / مسمى الإدارة:"))
        self.txt_supervising_doctor = QLineEdit()
        text_box.addWidget(self.txt_supervising_doctor)

        text_box.addWidget(QLabel("الشعار النصي (Tagline):"))
        self.txt_tagline = QLineEdit()
        text_box.addWidget(self.txt_tagline)

        text_box.addWidget(QLabel("العنوان ورقم التليفون:"))
        self.txt_address = QLineEdit()
        self.txt_phones = QLineEdit()
        text_box.addWidget(self.txt_address)
        text_box.addWidget(self.txt_phones)

        text_box.addWidget(QLabel("الملاحظات السفلية التلقائية للتقرير (Footer Notes / Seal Text):"))
        self.txt_footer_notes = QTextEdit()
        self.txt_footer_notes.setMaximumHeight(85)
        text_box.addWidget(self.txt_footer_notes)

        text_layout.addWidget(text_card)
        text_layout.addStretch()
        text_scroll.setWidget(text_widget)
        self.tabs.addTab(text_scroll, "📝 النصوص والبيانات")

        control_layout.addWidget(self.tabs)

        # Bottom Action Bar
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        self.btn_save = AnimatedButton("💾 حفظ الإعدادات")
        self.btn_save.clicked.connect(self.save_settings)

        self.btn_preview_report = QPushButton("👁️ معاينة تقرير نتيجة")
        self.btn_preview_report.clicked.connect(self.preview_report)

        self.btn_preview_invoice = QPushButton("🧾 معاينة فاتورة")
        self.btn_preview_invoice.clicked.connect(self.preview_invoice)

        btn_box.addWidget(self.btn_save)
        btn_box.addWidget(self.btn_preview_report)
        btn_box.addWidget(self.btn_preview_invoice)
        control_layout.addLayout(btn_box)

        main_layout.addWidget(control_frame, 1)

        # -------------------------------------------------------------------
        # Right Panel: Live PDF Preview Status / Placeholder
        # -------------------------------------------------------------------
        preview_frame = QFrame()
        preview_frame.setObjectName("Card")
        preview_frame.setStyleSheet("QFrame#Card { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 10px; }")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)

        preview_title = QLabel("🖼️ المعاينة المباشرة للمخرجات")
        preview_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #0B4F6C;")
        preview_layout.addWidget(preview_title)

        self.lbl_preview_info = QLabel("اختر الألوان والهوامش واضغط على زر المعاينة للاطلاع على نتيجة تصميم الـ PDF فورياً.")
        self.lbl_preview_info.setWordWrap(True)
        self.lbl_preview_info.setStyleSheet("color: #64748B; font-size: 13px;")
        preview_layout.addWidget(self.lbl_preview_info)

        self.preview_status_box = QLabel("اضغط 'معاينة تقرير نتيجة' أو 'معاينة فاتورة' لعرض الملف المطبوع بنمطك الجديد.")
        self.preview_status_box.setAlignment(Qt.AlignCenter)
        self.preview_status_box.setWordWrap(True)
        self.preview_status_box.setStyleSheet("background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 24px; color: #475569; font-size: 13px;")
        preview_layout.addWidget(self.preview_status_box, 1)

        main_layout.addWidget(preview_frame, 1)

    def load_settings(self):
        s = catalog_service.get_lab_settings()
        mode = s.get("pdf_paper_mode", "white_paper")
        if mode == "pre_printed":
            self.btn_preprinted.setChecked(True)
        else:
            self.btn_white_paper.setChecked(True)

        page_size = s.get("pdf_page_size", "A4")
        idx = self.combo_page_size.findText(page_size)
        if idx >= 0:
            self.combo_page_size.setCurrentIndex(idx)

        self.spin_top_margin.setValue(float(s.get("pdf_top_margin_mm", 15.0) or 15.0))
        self.spin_bottom_margin.setValue(float(s.get("pdf_bottom_margin_mm", 15.0) or 15.0))
        self.spin_right_margin.setValue(float(s.get("pdf_right_margin_mm", 12.0) or 12.0))
        self.spin_left_margin.setValue(float(s.get("pdf_left_margin_mm", 12.0) or 12.0))

        self.txt_primary_color.setText(s.get("brand_primary_color") or "#0B4F6C")
        self.chk_show_logo.setChecked(bool(s.get("pdf_header_show_logo", 1)))

        logo_align = s.get("pdf_logo_align", "right")
        idx_align = self.combo_logo_align.findData(logo_align)
        if idx_align >= 0:
            self.combo_logo_align.setCurrentIndex(idx_align)

        self.chk_show_signature.setChecked(bool(s.get("pdf_show_doctor_signature", 1)))
        self.txt_sig_title.setText(s.get("pdf_doctor_signature_title") or "طبيب التحاليل المسؤول")
        self.txt_sig_path.setText(s.get("pdf_doctor_signature_path") or "")

        self.chk_show_stamp.setChecked(bool(s.get("pdf_show_stamp", 1)))
        self.txt_stamp_path.setText(s.get("pdf_stamp_path") or "")

        self.txt_lab_name.setText(s.get("lab_name") or "")
        self.txt_supervising_doctor.setText(s.get("supervising_doctor_name") or "")
        self.txt_tagline.setText(s.get("tagline") or "")
        self.txt_address.setText(s.get("address") or "")
        self.txt_phones.setText(s.get("phone_numbers") or "")
        self.txt_footer_notes.setText(s.get("pdf_custom_footer_notes") or s.get("digital_seal_text") or "")

    def _collect_settings(self) -> dict:
        s = catalog_service.get_lab_settings()
        s["pdf_paper_mode"] = "pre_printed" if self.btn_preprinted.isChecked() else "white_paper"
        s["pdf_page_size"] = self.combo_page_size.currentText()
        s["pdf_top_margin_mm"] = self.spin_top_margin.value()
        s["pdf_bottom_margin_mm"] = self.spin_bottom_margin.value()
        s["pdf_right_margin_mm"] = self.spin_right_margin.value()
        s["pdf_left_margin_mm"] = self.spin_left_margin.value()

        s["brand_primary_color"] = self.txt_primary_color.text().strip() or "#0B4F6C"
        s["pdf_header_show_logo"] = 1 if self.chk_show_logo.isChecked() else 0
        s["pdf_logo_align"] = self.combo_logo_align.currentData() or "right"

        s["pdf_show_doctor_signature"] = 1 if self.chk_show_signature.isChecked() else 0
        s["pdf_doctor_signature_title"] = self.txt_sig_title.text().strip()
        s["pdf_doctor_signature_path"] = self.txt_sig_path.text().strip()

        s["pdf_show_stamp"] = 1 if self.chk_show_stamp.isChecked() else 0
        s["pdf_stamp_path"] = self.txt_stamp_path.text().strip()

        s["lab_name"] = self.txt_lab_name.text().strip()
        s["supervising_doctor_name"] = self.txt_supervising_doctor.text().strip()
        s["tagline"] = self.txt_tagline.text().strip()
        s["address"] = self.txt_address.text().strip()
        s["phone_numbers"] = self.txt_phones.text().strip()
        s["pdf_custom_footer_notes"] = self.txt_footer_notes.toPlainText().strip()
        return s

    def save_settings(self):
        try:
            s = self._collect_settings()
            user_id = getattr(self.user, "user_id", getattr(self.user, "id", None)) if self.user else None
            catalog_service.save_lab_settings(s, user_id=user_id)
            QMessageBox.information(self, "تم الحفظ", "تم حفظ إعدادات الـ PDF والتخصيص بنجاح! ✅")
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء حفظ الإعدادات: {exc}")

    def _pick_color(self):
        from PySide2.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self.txt_primary_color.text().strip()), self, "اختر اللون الرئيسي للتقرير")
        if c.isValid():
            self.txt_primary_color.setText(c.name())

    def _browse_signature(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختر صورة التوقيع", "", "Image Files (*.png *.jpg *.jpeg)")
        if path:
            self.txt_sig_path.setText(path)

    def _browse_stamp(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختر صورة ختم المعمل", "", "Image Files (*.png *.jpg *.jpeg)")
        if path:
            self.txt_stamp_path.setText(path)

    def preview_report(self):
        try:
            settings = self._collect_settings()
            sample_params = [
                {"name": "Hemoglobin (Hb)", "numeric_value": 14.5, "unit": "g/dL", "range_low": 12.0, "range_high": 16.0, "flag": "Normal"},
                {"name": "Fasting Blood Sugar", "numeric_value": 142.0, "unit": "mg/dL", "range_low": 70.0, "range_high": 110.0, "flag": "High"},
                {"name": "ALT (GPT)", "numeric_value": 28.0, "unit": "U/L", "range_low": 10.0, "range_high": 40.0, "flag": "Normal"},
            ]
            pdf_path = generate_lab_report_pdf(
                patient_name="أحمد محمود السعيد",
                gender="Male",
                age_years=35,
                test_name="صورة دم و فحص سكر صائم",
                parameters_with_values=sample_params,
                lab_settings=settings,
                invoice_number=9901
            )
            self._show_preview_result("تقرير نتيجة التحليل", pdf_path)
        except Exception as exc:
            QMessageBox.warning(self, "معاينة", f"فشل إنشاء المعاينة: {exc}")

    def preview_invoice(self):
        try:
            settings = self._collect_settings()
            sample_visit = {
                "invoice_number": 9901,
                "patient_name": "أحمد محمود السعيد",
                "visit_date": "2026-08-08T15:00:00",
                "total_amount": 350.0,
                "discount_amount": 50.0,
                "paid_amount": 300.0,
                "balance": 0.0,
                "doctor_name": "د. مصطفى الزناتي",
            }
            sample_orders = [
                {"test_name": "Complete Blood Count (CBC)", "price": 150.0},
                {"test_name": "Fasting Blood Sugar (FBS)", "price": 200.0},
            ]
            pdf_path = generate_invoice_pdf(sample_visit, sample_orders, settings)
            self._show_preview_result("فاتورة الزيارة", pdf_path)
        except Exception as exc:
            QMessageBox.warning(self, "معاينة", f"فشل إنشاء معاينة الفاتورة: {exc}")

    def _show_preview_result(self, title: str, pdf_path: str):
        if os.path.exists(pdf_path):
            file_size_kb = os.path.getsize(pdf_path) / 1024
            self.preview_status_box.setText(
                f"✅ تم إنشاء {title} بنجاح!\n\n"
                f"📁 المسار:\n{pdf_path}\n\n"
                f"📊 الحجم: {file_size_kb:.1f} KB\n\n"
                f"اضغط الزر أدناه لفتح الملف المطبوع مباشرة."
            )
            self.lbl_preview_info.setText(f"معاينة حديثة: {title}")
            if not hasattr(self, "btn_open_pdf"):
                self.btn_open_pdf = QPushButton("📂 فتح ملف الـ PDF المعاين")
                self.btn_open_pdf.clicked.connect(lambda: os.startfile(self._last_preview_pdf))
                self.preview_status_box.parentWidget().layout().addWidget(self.btn_open_pdf)
            self._last_preview_pdf = pdf_path
