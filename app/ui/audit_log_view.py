import csv
import os

from PySide2.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                                QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.config import BACKUPS_DIR
from app.services import audit_service
from app.ui.animated_button import AnimatedButton
from app.ui.widgets import HintBanner


class AuditLogView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user

        outer = QVBoxLayout(self)

        header_row = QHBoxLayout()
        title = QLabel("سجل التدقيق")
        title.setObjectName("PageTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        export_btn = AnimatedButton("تصدير السجل إلى CSV 📥")
        export_btn.setToolTip("تصدير نتائج البحث في سجل التدقيق لملف CSV لتسهيل التتبع والتحليل")
        export_btn.clicked.connect(self.export_csv)
        header_row.addWidget(export_btn)

        outer.addLayout(header_row)
        outer.addWidget(HintBanner(
            "سجل كامل بكل عملية إضافة أو تعديل أو حذف أو دفع في النظام، مع اسم من قام بها ووقتها. "
            "استخدم الفلاتر المتقدمة لتضييق النتائج حسب الشاشة، المستخدم، نوع الإجراء، أو التاريخ."
        ))

        filters_card = QFrame()
        filters_card.setObjectName("Card")
        filters_layout = QHBoxLayout(filters_card)

        filters_layout.addWidget(QLabel("الجدول/الشاشة"))
        self.table_combo = QComboBox()
        self.table_combo.addItem("(الكل)", "")
        filters_layout.addWidget(self.table_combo)

        filters_layout.addWidget(QLabel("المستخدم"))
        self.user_combo = QComboBox()
        self.user_combo.addItem("(الكل)", None)
        filters_layout.addWidget(self.user_combo)

        filters_layout.addWidget(QLabel("الإجراء"))
        self.action_combo = QComboBox()
        self.action_combo.addItem("(الكل)", "")
        filters_layout.addWidget(self.action_combo)

        filters_layout.addWidget(QLabel("من"))
        self.from_edit = QLineEdit()
        self.from_edit.setPlaceholderText("2026-01-01")
        filters_layout.addWidget(self.from_edit)

        filters_layout.addWidget(QLabel("إلى"))
        self.to_edit = QLineEdit()
        self.to_edit.setPlaceholderText("2026-12-31")
        filters_layout.addWidget(self.to_edit)

        search_button = AnimatedButton("بحث 🔍")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search)
        filters_layout.addWidget(search_button)

        outer.addWidget(filters_card)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["الوقت", "المستخدم", "الجدول/الشاشة", "المعرّف", "الإجراء", "التفاصيل"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        outer.addWidget(self.table)

        self.current_rows = []
        self._load_filters()
        self.search()

    def _load_filters(self):
        self.table_combo.clear()
        self.table_combo.addItem("(الكل)", "")
        for t in audit_service.get_distinct_tables():
            self.table_combo.addItem(t, t)

        self.user_combo.clear()
        self.user_combo.addItem("(الكل)", None)
        for u in audit_service.get_audit_users():
            self.user_combo.addItem(f"{u['username']} ({u['full_name']})", u["id"])

        self.action_combo.clear()
        self.action_combo.addItem("(الكل)", "")
        for act in audit_service.get_distinct_actions():
            self.action_combo.addItem(act, act)

    def refresh(self):
        self._load_filters()
        self.search()

    def search(self):
        table_val = self.table_combo.currentData() or ""
        user_val = self.user_combo.currentData()
        action_val = self.action_combo.currentData() or ""
        from_val = self.from_edit.text().strip()
        to_val = self.to_edit.text().strip()

        rows = audit_service.search_audit_logs(
            table_name=table_val,
            date_from=from_val,
            date_to=to_val,
            user_id=user_val,
            action=action_val,
        )
        self.current_rows = rows
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            values = [
                r["timestamp"], r.get("username") or "-", r["table_name"],
                str(r["row_id"]) if r["row_id"] is not None else "-", r["action"], r.get("details") or ""
            ]
            for col, value in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def export_csv(self):
        if not self.current_rows:
            QMessageBox.warning(self, "تنبيه", "لا توجد سجلات لتصديرها")
            return
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        path = os.path.join(BACKUPS_DIR, "audit_logs_report.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["الوقت", "المستخدم", "الجدول", "المعرف", "الإجراء", "التفاصيل"])
            for r in self.current_rows:
                writer.writerow([
                    r["timestamp"], r.get("username") or "-", r["table_name"],
                    str(r["row_id"]) if r["row_id"] is not None else "-", r["action"], r.get("details") or ""
                ])
        QMessageBox.information(self, "تم التصدير", f"تم تصدير سجل التدقيق بنجاح إلى:\n{path}")

