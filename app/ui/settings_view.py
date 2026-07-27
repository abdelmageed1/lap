from PySide2.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                                QPushButton, QTextEdit, QVBoxLayout, QWidget)

from PySide2.QtCore import Qt

from app.services import catalog_service
from app.ui.widgets import HintBanner


class SettingsView(QWidget):
    def __init__(self, user=None):
        super().__init__()
        self.user = user
        self.setObjectName("SettingsView")

        layout = QVBoxLayout(self)
        title = QLabel("الإعدادات")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(HintBanner("إدارة بيانات المعمل الأساسية مثل الاسم والعنوان والجهات والأطباء."))

        self._build_general_section(layout)
        self._build_catalog_section(layout)
        self._build_actions(layout)
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
        self.signature1_edit.setPlaceholderText("التوقيع 1")
        card_layout.addWidget(QLabel("توقيع الصفحة الأولى"))
        card_layout.addWidget(self.signature1_edit)

        self.signature2_edit = QLineEdit()
        self.signature2_edit.setPlaceholderText("التوقيع 2")
        card_layout.addWidget(QLabel("توقيع الصفحة الثانية"))
        card_layout.addWidget(self.signature2_edit)

        layout.addWidget(card)

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
        settings = {
            "lab_name": self.lab_name_edit.text().strip(),
            "tagline": self.tagline_edit.text().strip(),
            "address": self.address_edit.toPlainText().strip(),
            "phone_numbers": self.phone_edit.text().strip(),
            "footer_signature1": self.signature1_edit.text().strip(),
            "footer_signature2": self.signature2_edit.text().strip(),
        }
        catalog_service.save_lab_settings(settings)
        QMessageBox.information(self, "تم الحفظ", "تم حفظ إعدادات المعمل بنجاح")
        self.refresh()
