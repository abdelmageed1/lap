import subprocess
import sys

from PySide2.QtWidgets import (QCheckBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                                QListWidget, QPushButton, QVBoxLayout, QWidget)

from app.reports.invoice_report import generate_invoice_pdf
from app.services import catalog_service, visit_service
from app.services.result_service import STATUS_LABELS
from app.ui.widgets import HintBanner


class VisitsView(QWidget):
    def __init__(self):
        super().__init__()
        self.visits = []
        self.selected_visit_id = None
        self._limit = 50
        self._offset = 0

        outer = QVBoxLayout(self)
        title = QLabel("الزيارات والفواتير")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "ابحث عن أي زيارة سابقة باسم المريض، أو فعِّل 'مبالغ غير مسددة فقط' لمتابعة المديونيات. "
            "اضغط على زيارة لعرض تفاصيلها، تسجيل دفعة جديدة، أو إعادة طباعة الفاتورة."
        ))

        columns = QHBoxLayout()
        outer.addLayout(columns)

        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("ابحث باسم المريض أو الهاتف أو رقم الفاتورة أو التاريخ...")
        self.unpaid_check = QCheckBox("مبالغ غير مسددة فقط")
        self.unpaid_check.setToolTip("إظهار الزيارات التي لم تُسدَّد بالكامل فقط")
        search_button = QPushButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search)
        search_row.addWidget(self.search_edit)
        search_row.addWidget(search_button)
        left_layout.addLayout(search_row)
        left_layout.addWidget(self.unpaid_check)
        self.unpaid_check.stateChanged.connect(self.search)

        self.visits_list = QListWidget()
        self.visits_list.itemClicked.connect(self.show_visit)
        left_layout.addWidget(self.visits_list)
        columns.addWidget(left, 1)

        right = QFrame()
        right.setObjectName("Card")
        self.details_layout = QVBoxLayout(right)
        self.details_title = QLabel("اختر زيارة لعرض تفاصيلها")
        self.details_title.setStyleSheet("font-weight: bold; color: #0B4F6C;")
        self.details_layout.addWidget(self.details_title)
        self.details_body = QLabel("")
        self.details_body.setWordWrap(True)
        self.details_layout.addWidget(self.details_body)

        payment_row = QHBoxLayout()
        payment_row.addWidget(QLabel("مبلغ الدفعة"))
        self.payment_spin = QDoubleSpinBox()
        self.payment_spin.setRange(0, 100000)
        self.payment_spin.setToolTip("مبلغ الدفعة الجديدة المطلوب تسجيلها على هذه الزيارة")
        payment_row.addWidget(self.payment_spin)
        pay_button = QPushButton("تسجيل دفعة")
        pay_button.setObjectName("Primary")
        pay_button.clicked.connect(self.add_payment)
        payment_row.addWidget(pay_button)
        self.details_layout.addLayout(payment_row)

        reprint_button = QPushButton("إعادة طباعة الفاتورة")
        reprint_button.setToolTip("يعيد إنشاء وفتح ملف PDF لهذه الفاتورة للطباعة مرة أخرى")
        reprint_button.clicked.connect(self.reprint_invoice)
        self.details_layout.addWidget(reprint_button)
        self.details_layout.addStretch()

        columns.addWidget(right, 2)

        self.search()
        load_more_btn = QPushButton("تحميل المزيد")
        load_more_btn.clicked.connect(self.load_more)
        left_layout.addWidget(load_more_btn)

    def search(self):
        self._offset = 0
        self.visits = visit_service.search_visits(self.search_edit.text().strip(), self.unpaid_check.isChecked(), limit=self._limit, offset=self._offset)
        self.visits_list.clear()
        for v in self.visits:
            self.visits_list.addItem(f"فاتورة {v['invoice_number']} - {v['patient_name']} - متبقي {v['balance']:.2f}")

    def load_more(self):
        self._offset += self._limit
        more = visit_service.search_visits(self.search_edit.text().strip(), self.unpaid_check.isChecked(), limit=self._limit, offset=self._offset)
        if not more:
            return
        self.visits.extend(more)
        for v in more:
            self.visits_list.addItem(f"فاتورة {v['invoice_number']} - {v['patient_name']} - متبقي {v['balance']:.2f}")

    def show_visit(self, item):
        row = self.visits_list.row(item)
        self.selected_visit_id = self.visits[row]["id"]
        details = visit_service.get_visit_details(self.selected_visit_id)
        self.details_title.setText(f"فاتورة رقم {details['invoice_number']} - {details['patient_name']}")
        lines = [
            f"التاريخ: {details['visit_date']}",
            f"الإجمالي: {details['total_amount']:.2f}",
            f"الخصم: {details['discount_amount']:.2f}",
            f"المدفوع: {details['paid_amount']:.2f}",
            f"المتبقي: {details['balance']:.2f}",
            "",
            "التحاليل:",
        ]
        for o in details["orders"]:
            status_display = STATUS_LABELS.get(o["status"], o["status"])
            lines.append(f"• {o['test_name']} - {o['price']:.2f} - {status_display}")
        self.details_body.setText("\n".join(lines))

    def add_payment(self):
        if self.selected_visit_id is None or self.payment_spin.value() <= 0:
            return
        visit_service.add_payment(self.selected_visit_id, self.payment_spin.value())
        self.payment_spin.setValue(0)
        self.search()
        details = visit_service.get_visit_details(self.selected_visit_id)
        self.details_body.setText(f"تم تسجيل الدفعة. المتبقي الآن: {details['balance']:.2f}")

    def reprint_invoice(self):
        if self.selected_visit_id is None:
            return
        details = visit_service.get_visit_details(self.selected_visit_id)
        settings = catalog_service.get_lab_settings()
        path = generate_invoice_pdf(details, details["orders"], settings)
        self._open_file(path)
        self.details_body.setText("تم فتح نسخة جديدة من الفاتورة للطباعة.")

    def _open_file(self, path):
        try:
            if sys.platform == "win32":
                import os
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
