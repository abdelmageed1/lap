from PySide2.QtCore import QDate
from PySide2.QtWidgets import (QCheckBox, QDateEdit, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                                QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from app.services import result_service, visit_service
from app.services.result_service import FLAG_LABELS
from app.ui.animated_button import AnimatedButton
from app.ui.widgets import HintBanner


def _build_history_tree(patient_id: int, start_date: str = None, end_date: str = None) -> QTreeWidget:
    tree = QTreeWidget()
    tree.setHeaderLabels(["البيان", "القيمة", "الوحدة", "المدى الطبيعي", "الحالة"])
    tree.setColumnWidth(0, 180)
    tree.setColumnWidth(1, 90)
    tree.setColumnWidth(2, 90)
    tree.setColumnWidth(3, 140)
    tree.setColumnWidth(4, 110)

    history = result_service.get_patient_history(patient_id, start_date=start_date, end_date=end_date)
    if not history:
        msg = "لا توجد زيارات في هذه الفترة المحددة" if (start_date or end_date) else "لا توجد زيارات سابقة لهذا المريض"
        placeholder = QTreeWidgetItem([msg])
        tree.addTopLevelItem(placeholder)
        return tree

    for visit in history:
        date_display = (visit.get("visit_date") or "")[:16].replace("T", " ")
        visit_item = QTreeWidgetItem([f"زيارة رقم {visit['invoice_number']} - {date_display}"])
        visit_item.setFirstColumnSpanned(True)

        tests = {}
        for r in visit.get("results", []):
            tests.setdefault(r["test_name"], []).append(r)

        for test_name, rows in tests.items():
            test_item = QTreeWidgetItem(visit_item, [test_name])
            test_item.setFirstColumnSpanned(True)
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

                flag_display = FLAG_LABELS.get(r.get("flag"), r.get("flag") or "")
                QTreeWidgetItem(test_item, [
                    r["parameter_name"],
                    value_display,
                    r.get("unit") or "",
                    range_display,
                    flag_display
                ])

        if not tests:
            QTreeWidgetItem(visit_item, ["(لا توجد نتائج مُدخلة بعد لهذه الزيارة)"])

        tree.addTopLevelItem(visit_item)
        visit_item.setExpanded(True)

    return tree


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

            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #F8FAFC;
                    border: 1px solid #CBD5E1;
                    border-radius: 8px;
                }
            """)
            p_layout = QGridLayout(card)
            p_layout.setContentsMargins(12, 10, 12, 10)
            p_layout.setSpacing(6)

            p_layout.addWidget(QLabel(f"<b>👤 الاسم:</b> {full_name_str}"), 0, 0)
            p_layout.addWidget(QLabel(f"<b>📱 رقم التليفون:</b> {phone_str}"), 0, 1)
            p_layout.addWidget(QLabel(f"<b>⚧ الجنس والسن:</b> {gender_ar} ({age_str})"), 1, 0)
            p_layout.addWidget(QLabel(f"<b>📊 إجمالي الزيارات:</b> {patient.get('visit_count', 0)}"), 1, 1)
            layout.addWidget(card)

        layout.addWidget(_build_history_tree(patient_id))
        close_button = AnimatedButton("إغلاق")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class PatientHistoryView(QWidget):
    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()
        outer = QVBoxLayout(self)
        title = QLabel("سجل المريض")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "استخدم هذه الشاشة لمعرفة هل راجع مريض ما المعمل من قبل، وماذا عمل من تحاليل ونتائج. "
            "ابحث بالاسم أو رقم التليفون، ونطاق التاريخ، ثم اختر المريض من القائمة."
        ))

        columns = QHBoxLayout()
        outer.addLayout(columns)

        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._label_bold("البحث في سجل المرضى"))

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("اكتب اسم المريض أو رقم تليفونه...")
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
        self.date_from.dateChanged.connect(lambda _: self.search())
        self.date_to.dateChanged.connect(lambda _: self.search())

        date_filter_row.addWidget(self.use_date_filter)
        date_filter_row.addWidget(QLabel("من:"))
        date_filter_row.addWidget(self.date_from)
        date_filter_row.addWidget(QLabel("إلى:"))
        date_filter_row.addWidget(self.date_to)

        left_layout.addLayout(date_filter_row)

        self.patients_list = QListWidget()
        self.patients_list.itemClicked.connect(self.on_select_patient)
        left_layout.addWidget(self.patients_list)
        columns.addWidget(left, 1)

        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        self.history_title = self._label_bold("اختر مريضًا من نتائج البحث لعرض سجله")
        right_layout.addWidget(self.history_title)

        # Patient Info Profile Card
        self.patient_card = QFrame()
        self.patient_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        p_layout = QGridLayout(self.patient_card)
        p_layout.setContentsMargins(12, 10, 12, 10)
        p_layout.setSpacing(8)

        self.lbl_name = QLabel("<b>👤 اسم المريض:</b> -")
        self.lbl_phone = QLabel("<b>📱 رقم التليفون:</b> -")
        self.lbl_gender_age = QLabel("<b>⚧ الجنس والسن:</b> -")
        self.lbl_visits = QLabel("<b>📊 الزيارات:</b> -")

        p_layout.addWidget(self.lbl_name, 0, 0)
        p_layout.addWidget(self.lbl_phone, 0, 1)
        p_layout.addWidget(self.lbl_gender_age, 1, 0)
        p_layout.addWidget(self.lbl_visits, 1, 1)

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

    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold; color: #0B4F6C;")
        return label

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
        self.patients_list.clear()
        if self.patients:
            for p in self.patients:
                last_visit = (p.get("last_visit") or "بدون زيارات")[:10]
                self.patients_list.addItem(
                    f"{p['full_name']} - {p.get('phone') or '-'} - {p['visit_count']} زيارة - آخر زيارة: {last_visit}"
                )
        else:
            self.patients_list.addItem("لا يوجد مرضى مطبق عليهم هذا الفلتر")

    def on_select_patient(self, item):
        row = self.patients_list.row(item)
        if row < 0 or row >= len(self.patients):
            return
        patient = self.patients[row]
        self.history_title.setText(f"سجل المريض: {patient['full_name']}")

        gender_ar = "ذكر" if patient.get("gender") == "Male" else ("أنثى" if patient.get("gender") == "Female" else "-")
        age_str = f"{patient.get('age_years')} سنة" if patient.get('age_years') else "غير محدد"
        phone_str = patient.get("phone") or "غير مسجل"
        title_prefix = f"{patient.get('title')} " if patient.get('title') else ""
        full_name_str = f"{title_prefix}{patient['full_name']}"
        last_visit_str = (patient.get("last_visit") or "بدون زيارات")[:10]

        self.lbl_name.setText(f"<b>👤 اسم المريض:</b> {full_name_str}")
        self.lbl_phone.setText(f"<b>📱 رقم التليفون:</b> {phone_str}")
        self.lbl_gender_age.setText(f"<b>⚧ الجنس والسن:</b> {gender_ar} ({age_str})")
        self.lbl_visits.setText(f"<b>📊 الزيارات:</b> {patient.get('visit_count', 0)} زيارات (آخر زيارة: {last_visit_str})")

        summary = result_service.get_patient_result_summary(patient["id"])
        if summary["has_results"]:
            self.summary_label.setText(
                f"الحالة: متوفرة | آخر تحليل: {summary['latest_test_name'] or '-'}"
            )
            self.summary_label.setStyleSheet("color: #146C8E; margin-bottom: 6px;")
        else:
            self.summary_label.setText("الحالة: غير متوفرة | لا توجد نتائج مسجلة لهذا المريض بعد")
            self.summary_label.setStyleSheet("color: #B45309; margin-bottom: 6px;")

        if self.tree_placeholder is not None:
            self.right_layout.removeWidget(self.tree_placeholder)
            self.tree_placeholder.deleteLater()
        self.tree_placeholder = _build_history_tree(patient["id"])
        self.right_layout.addWidget(self.tree_placeholder)
