"""Patient history: search a patient by name/phone and see every past visit, test and result -
so a returning patient's previous work-up is one search away instead of being re-asked or re-found
by digging through the Visits screen invoice-by-invoice."""
from PySide2.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                                QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from app.services import result_service, visit_service
from app.services.result_service import FLAG_LABELS
from app.ui.widgets import HintBanner


def _build_history_tree(patient_id: int) -> QTreeWidget:
    tree = QTreeWidget()
    tree.setHeaderLabels(["البيان", "القيمة", "الوحدة", "الحالة"])
    tree.setColumnWidth(0, 260)

    history = result_service.get_patient_history(patient_id)
    if not history:
        placeholder = QTreeWidgetItem(["لا توجد زيارات سابقة لهذا المريض"])
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
                flag_display = FLAG_LABELS.get(r.get("flag"), r.get("flag") or "")
                QTreeWidgetItem(test_item, [r["parameter_name"], value_display, r.get("unit") or "", flag_display])

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
        self.resize(650, 500)
        layout = QVBoxLayout(self)
        title = QLabel(f"السجل الكامل للمريض: {patient_name}")
        title.setStyleSheet("font-weight: bold; color: #0B4F6C; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(_build_history_tree(patient_id))
        close_button = QPushButton("إغلاق")
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
            "ابحث بالاسم أو رقم التليفون، ثم اختر المريض من القائمة."
        ))

        columns = QHBoxLayout()
        outer.addLayout(columns)

        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._label_bold("البحث عن مريض (بالاسم أو رقم التليفون)"))
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("اكتب اسم المريض أو رقم تليفونه...")
        self.search_edit.setToolTip("اترك الحقل فارغًا واضغط بحث لعرض كل المرضى، الأحدث أولًا")
        self.search_edit.returnPressed.connect(self.search)
        search_button = QPushButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search)
        search_row.addWidget(self.search_edit)
        search_row.addWidget(search_button)
        left_layout.addLayout(search_row)

        self.patients_list = QListWidget()
        self.patients_list.itemClicked.connect(self.on_select_patient)
        left_layout.addWidget(self.patients_list)
        columns.addWidget(left, 1)

        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        self.history_title = self._label_bold("اختر مريضًا من نتائج البحث لعرض سجله")
        right_layout.addWidget(self.history_title)
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

    def refresh(self):
        self.search()

    def search(self):
        self.patients = visit_service.search_patients(self.search_edit.text().strip())
        self.patients_list.clear()
        for p in self.patients:
            last_visit = (p.get("last_visit") or "بدون زيارات")[:10]
            self.patients_list.addItem(
                f"{p['full_name']} - {p.get('phone') or '-'} - {p['visit_count']} زيارة - آخر زيارة: {last_visit}"
            )

    def on_select_patient(self, item):
        row = self.patients_list.row(item)
        patient = self.patients[row]
        self.history_title.setText(f"سجل المريض: {patient['full_name']}")
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
