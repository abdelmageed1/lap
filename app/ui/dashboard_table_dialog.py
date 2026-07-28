"""DashboardVisitsTableDialog – generic table dialog used by dashboard cards."""
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)


class DashboardVisitsTableDialog(QDialog):
    """Displays a list of visit/order records (list of dicts) in a sortable table dialog."""

    def __init__(self, title: str, records: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(820, 480)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout(self)

        heading = QLabel(title)
        heading.setStyleSheet("font-size:15px; font-weight:bold; color:#1E3A5F; margin-bottom:6px;")
        layout.addWidget(heading)

        count_label = QLabel(f"إجمالي السجلات: {len(records)}")
        count_label.setStyleSheet("color:#475569; margin-bottom:4px;")
        layout.addWidget(count_label)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                gridline-color: #E2E8F0;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #1E3A5F;
                color: white;
                font-weight: bold;
                padding: 6px;
            }
            QTableWidget::item:alternate {
                background-color: #F8FAFC;
            }
        """)

        if records:
            columns = list(records[0].keys())
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels(self._arabicize_headers(columns))
            self.table.setRowCount(len(records))
            for row_i, rec in enumerate(records):
                for col_i, key in enumerate(columns):
                    val = rec.get(key)
                    item = QTableWidgetItem(str(val) if val is not None else "")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_i, col_i, item)
        else:
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["البيان"])
            self.table.setRowCount(1)
            empty = QTableWidgetItem("لا توجد بيانات للعرض")
            empty.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(0, 0, empty)

        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("إغلاق")
        close_btn.setObjectName("Primary")
        close_btn.setFixedWidth(110)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    @staticmethod
    def _arabicize_headers(columns: list) -> list:
        """Map common English column names to Arabic labels for display."""
        mapping = {
            "id": "م",
            "invoice_number": "رقم الفاتورة",
            "visit_date": "تاريخ الزيارة",
            "total_amount": "الإجمالي",
            "paid_amount": "المدفوع",
            "discount_amount": "الخصم",
            "patient_name": "اسم المريض",
            "doctor_name": "الطبيب",
            "referral_source": "جهة الإحالة",
            "status": "الحالة",
            "test_name": "اسم التحليل",
            "ordered_at": "وقت الطلب",
            "amount": "المبلغ",
            "paid_at": "وقت الدفع",
        }
        return [mapping.get(col, col.replace("_", " ").title()) for col in columns]
