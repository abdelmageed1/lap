from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
                                QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.services import specimen_service
from app.ui.animated_button import AnimatedButton
from app.ui.widgets import HintBanner


class SpecimenTrackingView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        self.rows_data = []

        outer = QVBoxLayout(self)
        title = QLabel("متابعة العينات")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "تتبّع مرحلة كل عينة من السحب حتى انتهاء التحليل - منفصلة عن حالة إدخال النتيجة نفسها. "
            "اختر عينة واضغط 'نقل للمرحلة التالية' لتحديث حالتها."
        ))

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 ابحث باسم المريض، التحليل، أو رقم الفاتورة...")
        self.search_edit.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_edit)
        card_layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["رقم الفاتورة", "اسم المريض", "التحليل", "المرحلة الحالية", "الإجراء"])
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        card_layout.addWidget(self.table)

        outer.addWidget(card)

        self.refresh()

    def _current_user_id(self):
        return getattr(self.current_user, "user_id", None) if self.current_user else None

    def refresh(self, *_args):
        query = self.search_edit.text().strip()
        self.rows_data = specimen_service.get_pending_specimens(query)
        self.table.setRowCount(len(self.rows_data))
        for row_idx, r in enumerate(self.rows_data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(r["invoice_number"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(r["patient_name"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(r["test_name"]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(specimen_service.STAGE_LABELS[r["specimen_status"]]))

            advance_button = AnimatedButton("نقل للمرحلة التالية ▶")
            advance_button.setObjectName("Primary")
            advance_button.setMinimumWidth(180)
            advance_button.setMinimumHeight(32)
            advance_button.setStyleSheet("padding: 4px 14px; font-size: 13px; font-weight: bold;")
            advance_button.clicked.connect(lambda checked=False, order_id=r["order_id"]: self.advance(order_id))

            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(6, 4, 6, 4)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.addWidget(advance_button)

            self.table.setCellWidget(row_idx, 4, btn_container)

    def advance(self, order_id: int):
        specimen_service.advance_specimen_status(order_id, user_id=self._current_user_id())
        self.refresh()

