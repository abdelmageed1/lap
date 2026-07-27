from PySide2.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.services import audit_service
from app.ui.widgets import HintBanner


class AuditLogView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user

        outer = QVBoxLayout(self)
        title = QLabel("سجل التدقيق")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "سجل كامل بكل عملية إضافة أو تعديل أو حذف أو دفع في النظام، مع اسم من قام بها ووقتها. "
            "استخدم الفلاتر لتضييق النتائج على جدول أو فترة زمنية معيَّنة."
        ))

        filters_card = QFrame()
        filters_card.setObjectName("Card")
        filters_layout = QHBoxLayout(filters_card)

        filters_layout.addWidget(QLabel("الجدول"))
        self.table_combo = QComboBox()
        self.table_combo.addItem("(الكل)", "")
        self.table_combo.setToolTip("اسم الجدول/الشاشة المتأثرة بالعملية، مثل patients أو visits")
        filters_layout.addWidget(self.table_combo)

        filters_layout.addWidget(QLabel("من تاريخ"))
        self.from_edit = QLineEdit()
        self.from_edit.setPlaceholderText("2026-01-01")
        filters_layout.addWidget(self.from_edit)

        filters_layout.addWidget(QLabel("إلى تاريخ"))
        self.to_edit = QLineEdit()
        self.to_edit.setPlaceholderText("2026-12-31")
        filters_layout.addWidget(self.to_edit)

        search_button = QPushButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search)
        filters_layout.addWidget(search_button)

        outer.addWidget(filters_card)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["الوقت", "المستخدم", "الجدول", "المعرّف", "الإجراء", "التفاصيل"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        outer.addWidget(self.table)

        self._load_table_options()
        self.search()

    def _load_table_options(self):
        for t in audit_service.get_distinct_tables():
            self.table_combo.addItem(t, t)

    def refresh(self):
        self._load_table_options_preserving_selection()
        self.search()

    def _load_table_options_preserving_selection(self):
        current = self.table_combo.currentData()
        self.table_combo.clear()
        self.table_combo.addItem("(الكل)", "")
        for t in audit_service.get_distinct_tables():
            self.table_combo.addItem(t, t)
        idx = self.table_combo.findData(current)
        if idx >= 0:
            self.table_combo.setCurrentIndex(idx)

    def search(self):
        rows = audit_service.search_audit_logs(
            self.table_combo.currentData() or "", self.from_edit.text().strip(), self.to_edit.text().strip()
        )
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            values = [r["timestamp"], r.get("username") or "-", r["table_name"],
                      str(r["row_id"]) if r["row_id"] is not None else "-", r["action"], r.get("details") or ""]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
