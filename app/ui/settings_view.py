import os
from datetime import datetime

from PySide2.QtWidgets import (QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                                QMessageBox, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget)
from PySide2.QtCore import Qt

from app.config import get_storage_root, set_storage_root, get_pdf_reports_dir, get_pdf_invoices_dir, get_exports_patients_dir, get_exports_catalog_dir, get_backups_dir
from app.services import catalog_service
from app.ui.animated_button import AnimatedButton
from app.ui.styles import get_color
from app.ui.widgets import HintBanner
from app.utils.audit import log_action


class SettingsView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.setObjectName("SettingsView")

        # Outer layout: title + hint stay fixed at top, content scrolls below
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        title = QLabel("الإعدادات")
        title.setObjectName("PageTitle")
        title.setContentsMargins(16, 12, 16, 4)
        outer_layout.addWidget(title)
        hint = HintBanner("إدارة بيانات المعمل الأساسية مثل الاسم والعنوان والجهات والأطباء.")
        hint.setContentsMargins(16, 0, 16, 8)
        outer_layout.addWidget(hint)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)

        self._build_general_section(layout)
        self._build_branding_section(layout)
        self._build_catalog_section(layout)
        self._build_storage_section(layout)
        self._build_catalog_io_section(layout)
        self._build_actions(layout)

        scroll.setWidget(scroll_widget)
        outer_layout.addWidget(scroll, 1)
        self.refresh()

    def _build_general_section(self, layout):
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("البيانات الأساسية للمعمل"))

        self.lab_name_edit = QLineEdit()
        self.lab_name_edit.setPlaceholderText("اسم المعمل")
        card_layout.addWidget(QLabel("اسم المعمل"))
        card_layout.addWidget(self.lab_name_edit)

        self.tagline_edit = QLineEdit()
        self.tagline_edit.setPlaceholderText("شعار أو slogan")
        card_layout.addWidget(QLabel("الشعار/العبارة"))
        card_layout.addWidget(self.tagline_edit)

        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("العنوان")
        self.address_edit.setMaximumHeight(90)
        card_layout.addWidget(QLabel("العنوان"))
        card_layout.addWidget(self.address_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("أرقام الهاتف")
        card_layout.addWidget(QLabel("أرقام الهاتف"))
        card_layout.addWidget(self.phone_edit)

        self.signature1_edit = QLineEdit()
        self.signature1_edit.setPlaceholderText("مثال: د. أحمد - مدير المعمل")
        card_layout.addWidget(QLabel("توقيع واسم معتمد التقرير (توقيع 1)"))
        card_layout.addWidget(self.signature1_edit)

        self.signature2_edit = QLineEdit()
        self.signature2_edit.setPlaceholderText("مثال: الفني المراجع")
        card_layout.addWidget(QLabel("توقيع واسم المراجع (توقيع 2)"))
        card_layout.addWidget(self.signature2_edit)

        self.app_title_edit = QLineEdit()
        self.app_title_edit.setPlaceholderText("مثال: LapLIS - نظام إدارة معمل التحاليل الطبية")
        card_layout.addWidget(QLabel("عنوان النافذة الرئيسي (شريط العنوان العلوي)"))
        card_layout.addWidget(self.app_title_edit)

        self.seal_text_edit = QLineEdit()
        self.seal_text_edit.setPlaceholderText("🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً.")
        card_layout.addWidget(QLabel("نص الاعتماد والختم الرقمي (أسفل التقرير)"))
        card_layout.addWidget(self.seal_text_edit)

        layout.addWidget(card)

    def _build_branding_section(self, layout):
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        
        lbl_title = QLabel("🎨 الهوية البصرية والألوان الرسمية للمعمل (PDF & Header)")
        lbl_title.setStyleSheet(f"font-weight: bold; color: {get_color('primary_text')}; font-size: 13px;")
        card_layout.addWidget(lbl_title)

        hint = QLabel("تتحكم هذه الألوان في ترويسة هيدر التقرير، خطوط الاعتماد، وأشرطة جداول نتائج الـ PDF والتطبيق.")
        hint.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 11px;")
        card_layout.addWidget(hint)

        colors_layout = QHBoxLayout()
        
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("اللون الرئيسي (Primary Brand Color):"))
        self.brand_primary_edit = QLineEdit("#0B4F6C")
        self.brand_primary_edit.setPlaceholderText("كود اللون الأساسي مثل #0B4F6C")
        col1.addWidget(self.brand_primary_edit)
        colors_layout.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("اللون الفرعي (Secondary Accent Color):"))
        self.brand_secondary_edit = QLineEdit("#146C8E")
        self.brand_secondary_edit.setPlaceholderText("كود اللون الفرعي مثل #146C8E")
        col2.addWidget(self.brand_secondary_edit)
        colors_layout.addLayout(col2)

        card_layout.addLayout(colors_layout)

        preset_label = QLabel("اختيار سريع لنماذج ألوان المعامل الجاهزة:")
        preset_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {get_color('text_main')}; margin-top: 6px;")
        card_layout.addWidget(preset_label)

        presets_layout = QHBoxLayout()
        presets = [
            ("🔵 كحلي نيلي", "#0B4F6C", "#146C8E"),
            ("🟢 زمردي تيل", "#0D9488", "#0F766E"),
            ("🔷 أزرق ملكي", "#1E40AF", "#1D4ED8"),
            ("🟣 بنفسجي فخم", "#6D28D9", "#7C3AED"),
            ("🔴 أحمر قرمزي", "#991B1B", "#B91C1C"),
            ("🔘 رمادي أنيق", "#334155", "#475569"),
        ]

        for name, p_hex, s_hex in presets:
            btn = QPushButton(name)
            btn.setStyleSheet(f"background-color: {p_hex}; color: #FFFFFF; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
            btn.clicked.connect(lambda checked=False, p=p_hex, s=s_hex: self._set_brand_colors(p, s))
            presets_layout.addWidget(btn)

        card_layout.addLayout(presets_layout)
        layout.addWidget(card)

    def _set_brand_colors(self, primary: str, secondary: str):
        self.brand_primary_edit.setText(primary)
        self.brand_secondary_edit.setText(secondary)



    def _build_catalog_section(self, layout):
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("إدارة البيانات المرجعية"))

        row = QHBoxLayout()
        self.department_combo = QComboBox()
        self.department_combo.setEditable(False)
        self.department_combo.currentIndexChanged.connect(self.on_department_selected)
        row.addWidget(QLabel("القسم"))
        row.addWidget(self.department_combo)
        card_layout.addLayout(row)

        self.department_name_edit = QLineEdit()
        self.department_name_edit.setPlaceholderText("اسم قسم جديد/محدث")
        row2 = QHBoxLayout()
        row2.addWidget(self.department_name_edit)
        add_department_button = QPushButton("حفظ قسم")
        add_department_button.clicked.connect(self.add_department)
        row2.addWidget(add_department_button)
        delete_department_button = QPushButton("حذف")
        delete_department_button.clicked.connect(self.delete_department)
        row2.addWidget(delete_department_button)
        card_layout.addLayout(row2)

        self.source_combo = QComboBox()
        self.source_combo.setEditable(False)
        self.source_combo.currentIndexChanged.connect(self.on_source_selected)
        card_layout.addWidget(QLabel("جهة الإحالة"))
        card_layout.addWidget(self.source_combo)

        self.source_name_edit = QLineEdit()
        self.source_name_edit.setPlaceholderText("اسم جهة إحالة جديدة/محدثة")
        row3 = QHBoxLayout()
        row3.addWidget(self.source_name_edit)
        add_source_button = QPushButton("حفظ جهة")
        add_source_button.clicked.connect(self.add_source)
        row3.addWidget(add_source_button)
        delete_source_button = QPushButton("حذف")
        delete_source_button.clicked.connect(self.delete_source)
        row3.addWidget(delete_source_button)
        card_layout.addLayout(row3)

        self.doctor_combo = QComboBox()
        self.doctor_combo.setEditable(False)
        self.doctor_combo.currentIndexChanged.connect(self.on_doctor_selected)
        card_layout.addWidget(QLabel("الطبيب"))
        card_layout.addWidget(self.doctor_combo)

        self.doctor_name_edit = QLineEdit()
        self.doctor_name_edit.setPlaceholderText("اسم طبيب جديد/محدث")
        row4 = QHBoxLayout()
        row4.addWidget(self.doctor_name_edit)
        add_doctor_button = QPushButton("حفظ طبيب")
        add_doctor_button.clicked.connect(self.add_doctor)
        row4.addWidget(add_doctor_button)
        delete_doctor_button = QPushButton("حذف")
        delete_doctor_button.clicked.connect(self.delete_doctor)
        row4.addWidget(delete_doctor_button)
        card_layout.addLayout(row4)

        layout.addWidget(card)

    def _build_storage_section(self, layout):
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        header = QLabel("📁 إعدادات مسار التخزين")
        header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {get_color('primary_text')};")
        cl.addWidget(header)
        cl.addWidget(QLabel("المسار الجذر الحالي لجميع الملفات المُصدَّرة والنسخ الاحتياطية وملفات PDF:"))

        self.storage_root_label = QLabel(get_storage_root())
        self.storage_root_label.setStyleSheet(
            f"background:{get_color('bg_subtle')}; border:1px solid {get_color('border')}; border-radius:6px; padding:6px 10px; color:{get_color('text_emphasis')};"
        )
        self.storage_root_label.setWordWrap(True)
        cl.addWidget(self.storage_root_label)

        btn_change = AnimatedButton("تغيير مسار التخزين 📁")
        btn_change.setObjectName("Primary")
        btn_change.clicked.connect(self.on_change_storage_root)
        cl.addWidget(btn_change)

        # Sub-folder map labels
        self.lbl_pdf_reports = QLabel()
        self.lbl_pdf_invoices = QLabel()
        self.lbl_exports_patients = QLabel()
        self.lbl_exports_catalog = QLabel()
        self.lbl_backups = QLabel()
        for lbl in [self.lbl_pdf_reports, self.lbl_pdf_invoices,
                    self.lbl_exports_patients, self.lbl_exports_catalog, self.lbl_backups]:
            lbl.setStyleSheet(f"color:{get_color('text_main')}; padding: 2px 0;")
            cl.addWidget(lbl)

        self._refresh_storage_labels()
        layout.addWidget(card)

    def _refresh_storage_labels(self):
        self.storage_root_label.setText(get_storage_root())
        self.lbl_pdf_reports.setText(f"📄 تقارير PDF:       {get_pdf_reports_dir()}")
        self.lbl_pdf_invoices.setText(f"🧾 فواتير PDF:       {get_pdf_invoices_dir()}")
        self.lbl_exports_patients.setText(f"👥 بيانات المرضى CSV: {get_exports_patients_dir()}")
        self.lbl_exports_catalog.setText(f"🧪 كتالوج التحاليل:  {get_exports_catalog_dir()}")
        self.lbl_backups.setText(f"💾 النسخ الاحتياطية:  {get_backups_dir()}")

    def on_change_storage_root(self):
        current = get_storage_root()
        chosen = QFileDialog.getExistingDirectory(self, "اختر مسار التخزين الجذر", current)
        if not chosen:
            return
        set_storage_root(chosen)
        self._refresh_storage_labels()
        QMessageBox.information(
            self, "تم تغيير المسار",
            f"تم تغيير مسار التخزين بنجاح إلى:\n{chosen}\n\nجميع الملفات الجديدة ستُحفظ في هذا المسار."
        )

    def _build_catalog_io_section(self, layout):
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        header = QLabel("🧪 تصدير واستيراد كتالوج التحاليل")
        header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {get_color('primary_text')};")
        cl.addWidget(header)
        cl.addWidget(QLabel(
            "تصدير كامل كتالوج التحاليل (الأقسام، التحاليل، المعلمات، المدى الطبيعي، الأسعار) إلى ملف JSON،"
            " أو استيراده من ملف لنسخه إلى نظام آخر."
        ))

        row_btns = QHBoxLayout()

        btn_export_cat = QPushButton("تصدير كتالوج التحاليل 📤")
        btn_export_cat.setStyleSheet(
            "QPushButton{background:#0D9488;color:white;font-weight:bold;border-radius:6px;padding:6px 14px;}"
            "QPushButton:hover{background:#0F766E;}"
        )
        btn_export_cat.clicked.connect(self.on_export_catalog)
        row_btns.addWidget(btn_export_cat)

        btn_import_cat = QPushButton("استيراد كتالوج من ملف 📥")
        btn_import_cat.setStyleSheet(
            "QPushButton{background:#0284C7;color:white;font-weight:bold;border-radius:6px;padding:6px 14px;}"
            "QPushButton:hover{background:#0369A1;}"
        )
        btn_import_cat.clicked.connect(self.on_import_catalog)
        row_btns.addWidget(btn_import_cat)
        row_btns.addStretch()
        cl.addLayout(row_btns)
        layout.addWidget(card)

    def on_export_catalog(self):
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        default_path = os.path.join(get_exports_catalog_dir(), f"catalog_{stamp}.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "تصدير كتالوج التحاليل", default_path, "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            count, msg = catalog_service.export_catalog_to_json(path)
            QMessageBox.information(
                self, "✅ تم التصدير بنجاح",
                f"{msg}\n\n📁 مسار الحفظ:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "خطأ بالتصدير", f"تعذر تصدير الكتالوج: {exc}")

    def on_import_catalog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "استيراد كتالوج تحاليل", get_exports_catalog_dir(), "JSON Files (*.json)"
        )
        if not path:
            return
        added, updated, errors, msg = catalog_service.import_catalog_from_json(path)
        detail = msg
        if errors:
            detail += "\n\nأخطاء:\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "نتيجة الاستيراد", detail)

    def _build_actions(self, layout):
        row = QHBoxLayout()
        save_button = QPushButton("حفظ الإعدادات")
        save_button.setObjectName("Primary")
        save_button.clicked.connect(self.save_settings)
        row.addWidget(save_button)

        refresh_button = QPushButton("تحديث")
        refresh_button.clicked.connect(self.refresh)
        row.addWidget(refresh_button)
        layout.addLayout(row)

    def refresh(self):
        data = catalog_service.get_settings_dashboard_data()
        settings = data.get("lab_settings") or {}
        self.lab_name_edit.setText(settings.get("lab_name") or "")
        self.tagline_edit.setText(settings.get("tagline") or "")
        self.address_edit.setPlainText(settings.get("address") or "")
        self.phone_edit.setText(settings.get("phone_numbers") or "")
        self.signature1_edit.setText(settings.get("footer_signature1") or "")
        self.signature2_edit.setText(settings.get("footer_signature2") or "")
        self.seal_text_edit.setText(
            settings.get("digital_seal_text") or "🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً."
        )
        self.app_title_edit.setText(
            settings.get("app_title") or "LapLIS - نظام إدارة معمل التحاليل الطبية"
        )
        self.brand_primary_edit.setText(settings.get("brand_primary_color") or "#0B4F6C")
        self.brand_secondary_edit.setText(settings.get("brand_secondary_color") or "#146C8E")

        self.department_combo.clear()
        self.department_combo.addItem("- اختر قسم -", None)
        for dept in data.get("departments") or []:
            self.department_combo.addItem(dept["name"], dept["id"])

        self.source_combo.clear()
        self.source_combo.addItem("- اختر جهة -", None)
        for source in data.get("referral_sources") or []:
            self.source_combo.addItem(source["name"], source["id"])

        self.doctor_combo.clear()
        self.doctor_combo.addItem("- اختر طبيب -", None)
        for doctor in data.get("doctors") or []:
            self.doctor_combo.addItem(doctor["full_name"], doctor["id"])

        self.department_name_edit.clear()
        self.source_name_edit.clear()
        self.doctor_name_edit.clear()

    def on_department_selected(self, _index):
        selected_id = self.department_combo.currentData()
        if selected_id is None:
            self.department_name_edit.clear()
            return
        text = self.department_combo.currentText()
        self.department_name_edit.setText(text)

    def add_department(self):
        name = self.department_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم القسم أولًا")
            return
        selected_id = self.department_combo.currentData()
        catalog_service.save_department({"id": selected_id, "name": name})
        self.department_name_edit.clear()
        self.refresh()
        QMessageBox.information(self, "تم الحفظ", "تم حفظ القسم بنجاح")

    def delete_department(self):
        selected_id = self.department_combo.currentData()
        if selected_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر قسمًا أولًا")
            return
        ok, message = catalog_service.delete_department(selected_id)
        if not ok:
            QMessageBox.warning(self, "تنبيه", message)
            return
        self.refresh()
        QMessageBox.information(self, "تم الحذف", message)

    def on_source_selected(self, _index):
        selected_id = self.source_combo.currentData()
        if selected_id is None:
            self.source_name_edit.clear()
            return
        self.source_name_edit.setText(self.source_combo.currentText())

    def add_source(self):
        name = self.source_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم جهة الإحالة أولًا")
            return
        selected_id = self.source_combo.currentData()
        catalog_service.save_referral_source(name, source_id=selected_id)
        self.source_name_edit.clear()
        self.refresh()
        QMessageBox.information(self, "تم الحفظ", "تم حفظ جهة الإحالة بنجاح")

    def delete_source(self):
        selected_id = self.source_combo.currentData()
        if selected_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر جهة إحالة أولًا")
            return
        catalog_service.deactivate_referral_source(selected_id)
        self.refresh()
        QMessageBox.information(self, "تم الحذف", "تم حذف جهة الإحالة من العرض")

    def on_doctor_selected(self, _index):
        selected_id = self.doctor_combo.currentData()
        if selected_id is None:
            self.doctor_name_edit.clear()
            return
        self.doctor_name_edit.setText(self.doctor_combo.currentText())

    def add_doctor(self):
        name = self.doctor_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "تنبيه", "أدخل اسم الطبيب أولًا")
            return
        selected_id = self.doctor_combo.currentData()
        catalog_service.save_doctor(name, doctor_id=selected_id)
        self.doctor_name_edit.clear()
        self.refresh()
        QMessageBox.information(self, "تم الحفظ", "تم حفظ الطبيب بنجاح")

    def delete_doctor(self):
        selected_id = self.doctor_combo.currentData()
        if selected_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر طبيبًا أولًا")
            return
        catalog_service.deactivate_doctor(selected_id)
        self.refresh()
        QMessageBox.information(self, "تم الحذف", "تم حذف الطبيب من العرض")

    def save_settings(self):
        new_title = self.app_title_edit.text().strip() or "LapLIS - نظام إدارة معمل التحاليل الطبية"
        settings = {
            "lab_name": self.lab_name_edit.text().strip(),
            "tagline": self.tagline_edit.text().strip(),
            "address": self.address_edit.toPlainText().strip(),
            "phone_numbers": self.phone_edit.text().strip(),
            "footer_signature1": self.signature1_edit.text().strip(),
            "footer_signature2": self.signature2_edit.text().strip(),
            "digital_seal_text": self.seal_text_edit.text().strip(),
            "app_title": new_title,
            "brand_primary_color": self.brand_primary_edit.text().strip() or "#0B4F6C",
            "brand_secondary_color": self.brand_secondary_edit.text().strip() or "#146C8E",
        }
        catalog_service.save_lab_settings(settings)
        # Audit: record who changed lab settings
        user_id = getattr(self.user, "user_id", None) if self.user else None
        log_action(
            "lab_settings", None, "save_lab_settings",
            user_id=user_id,
            details=f"lab_name={settings.get('lab_name', '')}",
        )
        if self.window():
            self.window().setWindowTitle(new_title)
        QMessageBox.information(self, "تم الحفظ", "تم حفظ إعدادات المعمل بنجاح")
        self.refresh()


