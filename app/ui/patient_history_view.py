import os
import subprocess
import sys
from PySide2.QtCore import QDate, Qt
from PySide2.QtGui import QColor, QFont
from PySide2.QtWidgets import (QCheckBox, QDateEdit, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                                QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from app.reports.lab_report import generate_lab_report_pdf
from app.services import auth_service, catalog_service, result_service, visit_service
from app.services.result_service import FLAG_LABELS
from app.ui.animated_button import AnimatedButton
from app.ui.widgets import HintBanner
from app.ui.styles import get_color, get_saved_theme


def _build_history_tree(patient_id: int, start_date: str = None, end_date: str = None) -> QTreeWidget:
    tree = QTreeWidget()
    tree.setHeaderLabels(["البيان", "القيمة", "الوحدة", "المدى الطبيعي", "الحالة"])
    
    tree.setTextElideMode(Qt.ElideNone)
    tree.setIndentation(14)
    
    header = tree.header()
    header.setSectionResizeMode(0, QHeaderView.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    
    tree.setStyleSheet(f"""
        QTreeWidget {{
            background-color: {get_color('bg_card')};
            border: 1px solid {get_color('border')};
            border-radius: 8px;
            color: {get_color('text_main')};
            font-size: 13px;
        }}
        QTreeWidget::item {{
            padding: 6px 8px;
        }}
        QTreeWidget::item:selected {{
            background-color: {get_color('accent_bg')};
            color: {get_color('accent')};
            font-weight: bold;
        }}
        QHeaderView::section {{
            background-color: {get_color('primary')};
            color: #FFFFFF;
            font-weight: bold;
            padding: 8px 10px;
            border: none;
            font-size: 13px;
        }}
    """)

    history = result_service.get_patient_history(patient_id, start_date=start_date, end_date=end_date)
    if not history:
        msg = "لا توجد زيارات في هذه الفترة المحددة" if (start_date or end_date) else "لا توجد زيارات سابقة لهذا المريض"
        placeholder = QTreeWidgetItem([msg])
        tree.addTopLevelItem(placeholder)
        return tree

    FLAG_BADGES = {
        "High": "🔴 مرتفع ⬆️",
        "H": "🔴 مرتفع ⬆️",
        "Low": "🟡 منخفض ⬇️",
        "L": "🟡 منخفض ⬇️",
        "Normal": "🟢 طبيعي",
        "N": "🟢 طبيعي",
        "Panic": "⚡ حرج 🚨",
        "Critical": "⚡ حرج 🚨",
    }

    theme = get_saved_theme()
    is_dark = theme == "dark"

    visit_bg = QColor("#1E293B") if is_dark else QColor("#F1F5F9")
    visit_fg = QColor("#38BDF8") if is_dark else QColor("#0369A1")

    test_bg = QColor("#0F172A") if is_dark else QColor("#F8FAFC")
    test_fg = QColor("#F8FAFC") if is_dark else QColor("#0F172A")

    for visit in history:
        date_display = (visit.get("visit_date") or "")[:16].replace("T", " ")
        visit_text = f"📅 زيارة رقم #{visit['invoice_number']}  │  🕒 التاريخ: {date_display}"
        visit_item = QTreeWidgetItem([visit_text])
        visit_item.setFirstColumnSpanned(True)

        visit_font = QFont()
        visit_font.setBold(True)
        visit_font.setPointSize(10)
        visit_item.setFont(0, visit_font)
        visit_item.setBackground(0, visit_bg)
        visit_item.setForeground(0, visit_fg)

        tests = {}
        for r in visit.get("results", []):
            tests.setdefault(r["test_name"], []).append(r)

        for test_name, rows in tests.items():
            test_item = QTreeWidgetItem(visit_item, [f"🧪 {test_name}"])
            test_item.setFirstColumnSpanned(True)

            test_font = QFont()
            test_font.setBold(True)
            test_item.setFont(0, test_font)
            test_item.setBackground(0, test_bg)
            test_item.setForeground(0, test_fg)

            for r in rows:
                if r.get("numeric_value") is not None:
                    value_display = str(r["numeric_value"])
                else:
                    value_display = r.get("text_value") or "-"

                low = r.get("range_low")
                high = r.get("range_high")
                if low is not None and high is not None:
                    range_display = f"{low} - {high}"
                elif r.get("range_text"):
                    range_display = r["range_text"]
                else:
                    range_display = "-"

                raw_flag = r.get("flag") or ""
                flag_display = FLAG_BADGES.get(raw_flag, FLAG_LABELS.get(raw_flag, raw_flag or "🟢 طبيعي"))

                param_item = QTreeWidgetItem(test_item, [
                    r["parameter_name"],
                    value_display,
                    r.get("unit") or "-",
                    range_display,
                    flag_display
                ])

                # Color code flag column
                if "مرتفع" in flag_display or "High" in raw_flag or raw_flag == "H":
                    param_item.setForeground(4, QColor("#EF4444") if is_dark else QColor("#DC2626"))
                    param_item.setForeground(1, QColor("#EF4444") if is_dark else QColor("#DC2626"))
                elif "منخفض" in flag_display or "Low" in raw_flag or raw_flag == "L":
                    param_item.setForeground(4, QColor("#F59E0B") if is_dark else QColor("#D97706"))
                    param_item.setForeground(1, QColor("#F59E0B") if is_dark else QColor("#D97706"))
                elif "حرج" in flag_display or "Panic" in raw_flag:
                    param_item.setForeground(4, QColor("#F87171") if is_dark else QColor("#991B1B"))
                    param_item.setForeground(1, QColor("#F87171") if is_dark else QColor("#991B1B"))
                else:
                    param_item.setForeground(4, QColor("#4ADE80") if is_dark else QColor("#166534"))

            test_item.setExpanded(True)

        if not tests:
            QTreeWidgetItem(visit_item, ["(لا توجد نتائج مُدخلة بعد لهذه الزيارة)"])

        tree.addTopLevelItem(visit_item)
        visit_item.setExpanded(True)

    tree.expandAll()
    return tree


class AdminPasswordConfirmDialog(QDialog):
    """Dialog prompting for the Admin password before performing destructive actions like patient deletion."""

    def __init__(self, patient_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تأكيد حذف المريض")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        msg_label = QLabel(
            f"<b>⚠️ تحذير:</b> أنت على وشك حذف المريض <b>'{patient_name}'</b> وكافة زياراته ونتائجه نهائيًا.<br>"
            "أدخل كلمة سر الأدمن لتأكيد العملية:"
        )
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {get_color('text_main')}; font-size: 13px;")
        layout.addWidget(msg_label)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("كلمة سر الأدمن...")
        self.password_edit.returnPressed.connect(self.accept)
        layout.addWidget(self.password_edit)

        btn_layout = QHBoxLayout()
        cancel_btn = AnimatedButton("إلغاء")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = AnimatedButton("تأكيد الحذف")
        confirm_btn.setObjectName("Danger")
        confirm_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def get_password(self) -> str:
        return self.password_edit.text()


class PatientHistoryDialog(QDialog):
    """A read-only popup showing one patient's full history - used from Reception when an
    existing patient is matched, so staff can check prior results without leaving the form."""

    def __init__(self, patient_id: int, patient_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"سجل المريض: {patient_name}")
        self.resize(700, 540)
        layout = QVBoxLayout(self)

        patient = visit_service.get_patient_by_id(patient_id)
        if patient:
            gender_ar = "ذكر" if patient.get("gender") == "Male" else ("أنثى" if patient.get("gender") == "Female" else "-")
            age_str = f"{patient.get('age_years')} سنة" if patient.get('age_years') else "غير محدد"
            phone_str = patient.get("phone") or "غير مسجل"
            title_prefix = f"{patient.get('title')} " if patient.get('title') else ""
            full_name_str = f"{title_prefix}{patient['full_name']}"
            created_by_str = patient.get("created_by_name") or "غير محدد"

            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {get_color('bg_subtle')};
                    border: 1px solid {get_color('border_light')};
                    border-radius: 8px;
                }}
            """)
            p_layout = QGridLayout(card)
            p_layout.setContentsMargins(12, 10, 12, 10)
            p_layout.setSpacing(6)

            p_layout.addWidget(QLabel(f"<b>👤 الاسم:</b> {full_name_str}"), 0, 0)
            p_layout.addWidget(QLabel(f"<b>📱 رقم التليفون:</b> {phone_str}"), 0, 1)
            p_layout.addWidget(QLabel(f"<b>⚧ الجنس والسن:</b> {gender_ar} ({age_str})"), 1, 0)
            p_layout.addWidget(QLabel(f"<b>📊 إجمالي الزيارات:</b> {patient.get('visit_count', 0)}"), 1, 1)
            p_layout.addWidget(QLabel(f"<b>✍️ سجل بواسطة:</b> {created_by_str}"), 2, 0)
            layout.addWidget(card)


        layout.addWidget(_build_history_tree(patient_id))
        close_button = AnimatedButton("إغلاق")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class PatientHistoryView(QWidget):
    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-weight: bold; color: {get_color('primary_text')};")
        return label

    def __init__(self, current_user=None):
        self.current_user = current_user
        self.selected_patient = None
        super().__init__()
        outer = QVBoxLayout(self)
        title = QLabel("سجل المريض")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "استخدم هذه الشاشة لمعرفة هل راجع مريض ما المعمل من قبل، وماذا عمل من تحاليل ونتائج. "
            "ابحث بالاسم، رقم التليفون، أو رقم الزيارة (الفاتورة)، ثم اختر المريض من القائمة."
        ))

        # Admin Export / Import Bar
        admin_bar = QHBoxLayout()
        admin_bar.setSpacing(10)

        self.btn_export_patients = AnimatedButton("تصدير سجل المرضى 📤")
        self.btn_export_patients.setToolTip("تصدير سجلات جميع المرضى لملف CSV (يتطلب كلمة سر الأدمن)")
        self.btn_export_patients.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
        """)
        self.btn_export_patients.clicked.connect(self.on_export_patients)
        admin_bar.addWidget(self.btn_export_patients)

        self.btn_import_patients = AnimatedButton("استيراد مرضى من ملف 📥")
        self.btn_import_patients.setToolTip("استيراد قائمة مرضى جديدة من ملف CSV مع منع التكرار (يتطلب كلمة سر الأدمن)")
        self.btn_import_patients.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_import_patients.clicked.connect(self.on_import_patients)
        admin_bar.addWidget(self.btn_import_patients)

        admin_bar.addStretch()
        outer.addLayout(admin_bar)

        columns = QHBoxLayout()
        outer.addLayout(columns)

        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._label_bold("البحث في سجل المرضى"))

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 اكتب اسم المريض، رقم تليفونه، أو رقم الزيارة...")
        self.search_edit.setToolTip("اترك الحقل فارغًا واضغط بحث لعرض كل المرضى، الأحدث أولًا")

        self.search_edit.returnPressed.connect(self.search)
        search_button = AnimatedButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search)
        search_row.addWidget(self.search_edit)
        search_row.addWidget(search_button)
        left_layout.addLayout(search_row)

        # Date range filter controls for patient search
        date_filter_row = QHBoxLayout()
        self.use_date_filter = QCheckBox("تصفية المرضى بالتاريخ")
        self.use_date_filter.setStyleSheet("font-weight: bold; color: #0F172A;")

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setEnabled(False)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)

        self.use_date_filter.toggled.connect(self.on_toggle_date_filter)
        self.date_from.dateChanged.connect(lambda *args: self.search())
        self.date_to.dateChanged.connect(lambda *args: self.search())

        date_filter_row.addWidget(self.use_date_filter)
        date_filter_row.addWidget(QLabel("من:"))
        date_filter_row.addWidget(self.date_from)
        date_filter_row.addWidget(QLabel("إلى:"))
        date_filter_row.addWidget(self.date_to)

        left_layout.addLayout(date_filter_row)

        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(5)
        self.patients_table.setHorizontalHeaderLabels(["اسم المريض", "التليفون", "الجنس والسن", "الزيارات", "آخر زيارة"])
        self.patients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patients_table.setSelectionMode(QTableWidget.SingleSelection)
        self.patients_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.patients_table.setAlternatingRowColors(True)
        self.patients_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.patients_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.patients_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.patients_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.patients_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.patients_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {get_color('border')};
                border-radius: 8px;
                gridline-color: {get_color('border')};
                font-size: 12px;
                background-color: {get_color('bg_card')};
                color: {get_color('text_main')};
            }}
            QHeaderView::section {{
                background-color: {get_color('primary')};
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {get_color('accent_bg')};
                color: {get_color('accent')};
                font-weight: bold;
            }}
        """)
        self.patients_table.itemSelectionChanged.connect(self.on_select_patient)
        left_layout.addWidget(self.patients_table)
        columns.addWidget(left, 40)

        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)

        header_row = QHBoxLayout()
        self.history_title = self._label_bold("👈 اختر مريضًا من نتائج البحث لعرض سجله")
        header_row.addWidget(self.history_title)
        header_row.addStretch()

        # Quick Expand/Collapse Buttons
        self.btn_expand_all = AnimatedButton("توسيع الكل 📂")
        self.btn_expand_all.setToolTip("فتح وتوسيع كافة الزيارات والتحاليل في القائمة دون الحاجة للضغط")
        self.btn_expand_all.clicked.connect(lambda: self.tree_placeholder.expandAll() if self.tree_placeholder else None)

        self.btn_collapse_all = AnimatedButton("طي الكل 📁")
        self.btn_collapse_all.setToolTip("طي كافة الزيارات والتحاليل")
        self.btn_collapse_all.clicked.connect(lambda: self.tree_placeholder.collapseAll() if self.tree_placeholder else None)

        header_row.addWidget(self.btn_expand_all)
        header_row.addWidget(self.btn_collapse_all)

        # Print Lab Report Button
        self.btn_print_report = AnimatedButton("🖨️ طباعة تقرير النتيجة PDF")
        self.btn_print_report.setToolTip("توليد وطباعة تقرير نتائج التحاليل لهذا المريض بصيغة PDF")
        self.btn_print_report.setObjectName("Primary")
        self.btn_print_report.setVisible(False)
        self.btn_print_report.clicked.connect(self.on_print_lab_report)
        header_row.addWidget(self.btn_print_report)

        # Delete patient button
        self.delete_patient_btn = AnimatedButton("حذف المريض 🗑️")
        self.delete_patient_btn.setToolTip("حذف هذا المريض وجميع زياراته ونتائجه بالكامل (يتطلب كلمة سر الأدمن)")
        self.delete_patient_btn.setObjectName("Danger")
        self.delete_patient_btn.setVisible(False)
        self.delete_patient_btn.clicked.connect(self.on_delete_patient)
        header_row.addWidget(self.delete_patient_btn)

        right_layout.addLayout(header_row)

        # Patient Info Profile Card
        self.patient_card = QFrame()
        self.patient_card.setStyleSheet(f"""
            QFrame {{
                background-color: {get_color('bg_subtle')};
                border: 1px solid {get_color('border')};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        p_layout = QGridLayout(self.patient_card)
        p_layout.setContentsMargins(12, 10, 12, 10)
        p_layout.setSpacing(8)

        self.lbl_name = QLabel("<b>👤 اسم المريض:</b> -")
        self.lbl_phone = QLabel("<b>📱 رقم التليفون:</b> -")
        self.lbl_gender_age = QLabel("<b>⚧ الجنس والسن:</b> -")
        self.lbl_visits = QLabel("<b>📊 الزيارات:</b> -")
        self.lbl_created_by = QLabel("<b>✍️ سجل بواسطة:</b> -")

        for lbl in (self.lbl_name, self.lbl_phone, self.lbl_gender_age, self.lbl_visits, self.lbl_created_by):
            lbl.setStyleSheet(f"color: {get_color('text_main')}; font-size: 13px; border: none; background: transparent;")

        p_layout.addWidget(self.lbl_name, 0, 0)
        p_layout.addWidget(self.lbl_phone, 0, 1)
        p_layout.addWidget(self.lbl_gender_age, 1, 0)
        p_layout.addWidget(self.lbl_visits, 1, 1)
        p_layout.addWidget(self.lbl_created_by, 2, 0)

        right_layout.addWidget(self.patient_card)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #0B4F6C; margin-bottom: 6px;")
        right_layout.addWidget(self.summary_label)

        self.history_container = QVBoxLayout()
        right_layout.addLayout(self.history_container)
        self.tree_placeholder = None
        columns.addWidget(right, 2)

        self.patients = []
        self.right_layout = right_layout
        self.search()


    def _is_admin(self) -> bool:
        if not self.current_user:
            return True
        if hasattr(self.current_user, "can_delete") and self.current_user.can_delete("PatientHistory"):
            return True
        if hasattr(self.current_user, "role_name") and self.current_user.role_name in ("مدير النظام", "Admin"):
            return True
        return False

    def on_toggle_date_filter(self, enabled):
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)
        self.search()

    def refresh(self):
        self.search()

    def search(self):

        query = self.search_edit.text().strip()
        start_date = self.date_from.date().toString("yyyy-MM-dd") if self.use_date_filter.isChecked() else None
        end_date = self.date_to.date().toString("yyyy-MM-dd") if self.use_date_filter.isChecked() else None

        self.patients = visit_service.search_patients(query, start_date=start_date, end_date=end_date)
        self.patients_table.setRowCount(len(self.patients))
        if self.patients:
            for row, p in enumerate(self.patients):
                gender_ar = "ذكر" if p.get("gender") == "Male" else ("أنثى" if p.get("gender") == "Female" else "-")
                age_str = f"{p.get('age_years')} سنة" if p.get('age_years') else "غير محدد"
                gender_age_str = f"{gender_ar} ({age_str})"
                last_visit = (p.get("last_visit") or "بدون زيارات")[:10]
                title_prefix = f"{p.get('title')} " if p.get('title') else ""
                full_name_str = f"{title_prefix}{p['full_name']}"

                item_name = QTableWidgetItem(full_name_str)
                item_phone = QTableWidgetItem(p.get('phone') or '-')
                item_gender_age = QTableWidgetItem(gender_age_str)
                item_visits = QTableWidgetItem(str(p.get('visit_count', 0)))
                item_last = QTableWidgetItem(last_visit)

                for item in (item_name, item_phone, item_gender_age, item_visits, item_last):
                    item.setTextAlignment(Qt.AlignCenter)

                self.patients_table.setItem(row, 0, item_name)
                self.patients_table.setItem(row, 1, item_phone)
                self.patients_table.setItem(row, 2, item_gender_age)
                self.patients_table.setItem(row, 3, item_visits)
                self.patients_table.setItem(row, 4, item_last)
        else:
            self._clear_selected_patient()

    def _clear_selected_patient(self):
        self.selected_patient = None
        self.history_title.setText("اختر مريضًا من نتائج البحث لعرض سجله")
        self.lbl_name.setText("<b>👤 اسم المريض:</b> -")
        self.lbl_phone.setText("<b>📱 رقم التليفون:</b> -")
        self.lbl_gender_age.setText("<b>⚧ الجنس والسن:</b> -")
        self.lbl_visits.setText("<b>📊 الزيارات:</b> -")
        self.lbl_created_by.setText("<b>✍️ سجل بواسطة:</b> -")
        self.summary_label.setText("")
        self.delete_patient_btn.setVisible(False)
        self.btn_print_report.setVisible(False)
        if self.tree_placeholder is not None:
            self.right_layout.removeWidget(self.tree_placeholder)
            self.tree_placeholder.deleteLater()
            self.tree_placeholder = None

    def on_select_patient(self):
        selected_rows = self.patients_table.selectionModel().selectedRows()
        if not selected_rows:
            self._clear_selected_patient()
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.patients):
            self._clear_selected_patient()
            return
        patient = self.patients[row]
        self.selected_patient = patient
        self.history_title.setText(f"سجل المريض: {patient['full_name']}")

        if self._is_admin():
            self.delete_patient_btn.setVisible(True)
        else:
            self.delete_patient_btn.setVisible(False)

        gender_ar = "ذكر" if patient.get("gender") == "Male" else ("أنثى" if patient.get("gender") == "Female" else "-")
        age_str = f"{patient.get('age_years')} سنة" if patient.get('age_years') else "غير محدد"
        phone_str = patient.get("phone") or "غير مسجل"
        title_prefix = f"{patient.get('title')} " if patient.get('title') else ""
        full_name_str = f"{title_prefix}{patient['full_name']}"
        last_visit_str = (patient.get("last_visit") or "بدون زيارات")[:10]
        created_by_str = patient.get("created_by_name") or "غير محدد"

        self.lbl_name.setText(f"<b>👤 اسم المريض:</b> {full_name_str}")
        self.lbl_phone.setText(f"<b>📱 رقم التليفون:</b> {phone_str}")
        self.lbl_gender_age.setText(f"<b>⚧ الجنس والسن:</b> {gender_ar} ({age_str})")
        self.lbl_visits.setText(f"<b>📊 الزيارات:</b> {patient.get('visit_count', 0)} زيارات (آخر زيارة: {last_visit_str})")
        self.lbl_created_by.setText(f"<b>✍️ سجل بواسطة:</b> {created_by_str}")

        summary = result_service.get_patient_result_summary(patient["id"])
        if summary["has_results"]:
            self.summary_label.setText(
                f"الحالة: متوفرة | آخر تحليل: {summary['latest_test_name'] or '-'}"
            )
            self.summary_label.setStyleSheet("color: #146C8E; margin-bottom: 6px;")
            self.btn_print_report.setVisible(True)
        else:
            self.summary_label.setText("الحالة: غير متوفرة | لا توجد نتائج مسجلة لهذا المريض بعد")
            self.summary_label.setStyleSheet("color: #B45309; margin-bottom: 6px;")
            self.btn_print_report.setVisible(False)

        if self.tree_placeholder is not None:
            self.right_layout.removeWidget(self.tree_placeholder)
            self.tree_placeholder.deleteLater()
        self.tree_placeholder = _build_history_tree(patient["id"])
        self.right_layout.addWidget(self.tree_placeholder)

    def on_print_lab_report(self):
        if not self.selected_patient:
            QMessageBox.warning(self, "تنبيه", "رجاءً اختر مريضًا من الجدول أولاً.")
            return

        patient_id = self.selected_patient["id"]
        summary = result_service.get_patient_result_summary(patient_id)
        order_id = summary.get("latest_order_id")
        if not order_id:
            QMessageBox.warning(self, "تنبيه", "لا توجد نتائج مسجلة لهذا المريض لطباعتها.")
            return

        order_details = result_service.get_order_print_details(order_id)
        if not order_details or not order_details.get("parameters"):
            QMessageBox.warning(self, "تنبيه", "لم يتم العثور على أية نتائج أو معلمات مدخلة لهذا التحليل بعد.")
            return

        lab_settings = catalog_service.get_lab_settings()
        try:
            pdf_path = generate_lab_report_pdf(
                patient_name=order_details["patient_name"],
                gender=order_details["gender"],
                age_years=order_details["age_years"],
                test_name=order_details["test_name"],
                parameters_with_values=order_details["parameters"],
                lab_settings=lab_settings,
                invoice_number=order_details["invoice_number"],
            )

            if sys.platform == "win32":
                os.startfile(pdf_path)
            else:
                subprocess.Popen(["xdg-open", pdf_path])

            QMessageBox.information(
                self, "✅ تم إصدَار التقرير",
                f"تم توليد وطباعة التقرير بنجاح!\n\n📁 مسار الحفظ:\n{pdf_path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "خطأ في الطباعة", f"تعذر إنشاء التقرير PDF:\n{exc}")

    def on_delete_patient(self):

        if not self.selected_patient:
            return

        patient = self.selected_patient
        dlg = AdminPasswordConfirmDialog(patient["full_name"], self)
        if dlg.exec_() == QDialog.Accepted:
            password = dlg.get_password().strip()
            if not password:
                QMessageBox.warning(self, "خطأ", "يجب إدخال كلمة سر الأدمن لتأكيد الحذف.")
                return

            user_id = getattr(self.current_user, "user_id", None) if self.current_user else None

            if not auth_service.verify_admin_password(password, user_id=user_id):
                QMessageBox.warning(self, "خطأ في التأكيد", "كلمة سر الأدمن غير صحيحة! تعذر إتمام عملية الحذف.")
                return

            ok, msg = visit_service.delete_patient(patient["id"], user_id=user_id)
            if ok:
                QMessageBox.information(self, "نجاح الحذف", msg)
                self._clear_selected_patient()
                self.search()
            else:
                QMessageBox.critical(self, "خطأ بالحذف", msg)

    def _verify_admin(self, title_action: str) -> bool:
        dlg = AdminPasswordConfirmDialog(title_action, self)
        if dlg.exec_() != QDialog.Accepted:
            return False
        pwd = dlg.get_password().strip()
        if not pwd:
            QMessageBox.warning(self, "خطأ الأمان", "يجب إدخال كلمة سر الأدمن لتأكيد العملية.")
            return False
        curr_uid = getattr(self.current_user, "user_id", None) if self.current_user else None
        if not auth_service.verify_admin_password(pwd, user_id=curr_uid):
            QMessageBox.warning(self, "خطأ الأمان", "كلمة سر الأدمن غير صحيحة! تعذر تنفيذ العملية.")
            return False
        return True

    def on_export_patients(self):
        if not self._verify_admin("تأكيد تصدير سجل المرضى"):
            return

        patients_data = visit_service.export_patients_data()
        if not patients_data:
            QMessageBox.information(self, "تنبيه", "لا توجد سجلات مرضى لتصديرها.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "تصدير سجل المرضى والعملاء",
            os.path.join(__import__("app.config", fromlist=["get_exports_patients_dir"]).get_exports_patients_dir(), "patients_database.csv"),
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = ["ID", "اسم المريض", "رقم التليفون", "الجنس", "السن بالسنوات", "اللقب", "عدد الزيارات", "آخر زيارة"]
                writer.writerow(headers)

                for p in patients_data:
                    gender_ar = "ذكر" if p.get("gender") == "Male" else "أنثى"
                    last_v = (p.get("last_visit") or "")[:16].replace("T", " ")
                    writer.writerow([
                        p.get("id"),
                        p.get("full_name"),
                        p.get("phone") or "",
                        gender_ar,
                        p.get("age_years") or 0,
                        p.get("title") or "",
                        p.get("visit_count") or 0,
                        last_v
                    ])

            QMessageBox.information(
                self, "✅ تم التصدير بنجاح",
                f"تم تصدير {len(patients_data)} سجل مريض بنجاح!\n\n"
                f"📁 مسار الحفظ:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "خطأ بالتصدير", f"تعذر حفظ الملف: {exc}")

    def on_import_patients(self):
        if not self._verify_admin("تأكيد استيراد سجل مرضى من ملف"):
            return

        path, _ = QFileDialog.getOpenFileName(self, "اختر ملف المرضى للاستيراد", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            imported_rows = []
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    imported_rows.append(dict(row))

            curr_uid = getattr(self.current_user, "user_id", None) if self.current_user else None
            created, updated, msg = visit_service.import_patients_data(imported_rows, current_user_id=curr_uid)
            QMessageBox.information(self, "نتيجة الاستيراد", msg)
            self.search()
        except Exception as exc:
            QMessageBox.critical(self, "خطأ بالاستيراد", f"تعذر قراءة أو استيراد الملف: {exc}")

