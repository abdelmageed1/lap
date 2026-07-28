import os
import subprocess
import sys

from PySide2.QtCore import Qt
from PySide2.QtGui import QColor
from PySide2.QtWidgets import (QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                                QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.reports.invoice_report import generate_invoice_pdf
from app.services import catalog_service, visit_service
from app.services.result_service import STATUS_LABELS
from app.ui.animated_button import AnimatedButton
from app.ui.widgets import HintBanner


class VisitsView(QWidget):
    def __init__(self):
        super().__init__()
        self.visits = []
        self.selected_visit_id = None
        self._limit = 50
        self._offset = 0

        outer = QVBoxLayout(self)
        title = QLabel("الزيارات والفواتير المالية")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "ابحث عن أية زيارة سابقة باسم المريض، رقم التليفون، أو رقم الفاتورة. "
            "اختر زيارة من الجدول لمراجعة تفاصيل الفاتورة، التحاليل المطلوبة، إدخال دفعة جديدة، أو إعادة الطباعة."
        ))

        columns = QHBoxLayout()
        outer.addLayout(columns)

        # Left Column - Visits Table
        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 ابحث باسم المريض، رقم التليفون، أو رقم الفاتورة...")
        self.search_edit.returnPressed.connect(self.search)

        self.unpaid_check = QCheckBox("مبالغ متبقية فقط")
        self.unpaid_check.setStyleSheet("font-weight: bold; color: #0F172A;")
        self.unpaid_check.setToolTip("إظهار الزيارات التي لم تُسدَّد بالكامل فقط")
        self.unpaid_check.stateChanged.connect(self.search)

        search_button = AnimatedButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search)

        search_row.addWidget(self.search_edit)
        search_row.addWidget(search_button)
        left_layout.addLayout(search_row)
        left_layout.addWidget(self.unpaid_check)

        self.visits_table = QTableWidget()
        self.visits_table.setColumnCount(6)
        self.visits_table.setHorizontalHeaderLabels([
            "الفاتورة", "اسم المريض", "تاريخ الزيارة", "الإجمالي", "المدفوع", "المتبقي"
        ])
        self.visits_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.visits_table.setSelectionMode(QTableWidget.SingleSelection)
        self.visits_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.visits_table.setAlternatingRowColors(True)
        self.visits_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.visits_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                gridline-color: #E2E8F0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1E3A5F;
                color: white;
                font-weight: bold;
                padding: 5px;
            }
        """)
        self.visits_table.itemSelectionChanged.connect(self.on_select_visit_row)
        left_layout.addWidget(self.visits_table)

        load_more_btn = AnimatedButton("تحميل المزيد ➕")
        load_more_btn.clicked.connect(self.load_more)
        left_layout.addWidget(load_more_btn)

        columns.addWidget(left, 3)

        # Right Column - Invoice & Test Order Details Card
        right = QFrame()
        right.setObjectName("Card")
        self.details_layout = QVBoxLayout(right)

        self.details_title = QLabel("اختر فاتورة من الجدول لعرض تفاصيلها")
        self.details_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #0B4F6C;")
        self.details_layout.addWidget(self.details_title)

        # Financial Summary Profile Grid
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        s_layout = QGridLayout(self.summary_card)
        s_layout.setContentsMargins(10, 8, 10, 8)
        s_layout.setSpacing(6)

        self.lbl_patient = QLabel("<b>👤 المريض:</b> -")
        self.lbl_date_time = QLabel("<b>📅 التاريخ:</b> -")
        self.lbl_total = QLabel("<b>💰 الإجمالي:</b> -")
        self.lbl_discount = QLabel("<b>🏷️ الخصم:</b> -")
        self.lbl_paid = QLabel("<b>💵 المدفوع:</b> -")
        self.lbl_balance = QLabel("<b>⚠️ المتبقي:</b> -")

        s_layout.addWidget(self.lbl_patient, 0, 0, 1, 2)
        s_layout.addWidget(self.lbl_date_time, 1, 0, 1, 2)
        s_layout.addWidget(self.lbl_total, 2, 0)
        s_layout.addWidget(self.lbl_discount, 2, 1)
        s_layout.addWidget(self.lbl_paid, 3, 0)
        s_layout.addWidget(self.lbl_balance, 3, 1)

        self.details_layout.addWidget(self.summary_card)

        # Requested Tests Section Header
        self.details_layout.addWidget(QLabel("<b>🧪 التحاليل المطلوبة في هذه الفاتورة:</b>"))

        # Tests Table Widget
        self.tests_table = QTableWidget()
        self.tests_table.setColumnCount(3)
        self.tests_table.setHorizontalHeaderLabels(["التحليل", "السعر", "الحالة"])
        self.tests_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tests_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tests_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #334155;
                color: white;
                font-weight: bold;
                padding: 4px;
            }
        """)
        self.details_layout.addWidget(self.tests_table)

        # Payment Registration Card
        payment_box = QFrame()
        payment_box.setStyleSheet("background-color: #F1F5F9; border-radius: 6px; padding: 6px;")
        payment_layout = QHBoxLayout(payment_box)
        payment_layout.setContentsMargins(4, 4, 4, 4)

        payment_layout.addWidget(QLabel("<b>تسجيل دفعة جديدة:</b>"))
        self.payment_spin = QDoubleSpinBox()
        self.payment_spin.setRange(0, 100000)
        self.payment_spin.setSuffix(" ج.م")
        self.payment_spin.setToolTip("مبلغ الدفعة الجديدة المطلوب تسجيلها على هذه الزيارة")
        payment_layout.addWidget(self.payment_spin)

        self.btn_pay = AnimatedButton("تسجيل الدفعة 💵")
        self.btn_pay.setObjectName("Primary")
        self.btn_pay.clicked.connect(self.add_payment)
        payment_layout.addWidget(self.btn_pay)

        self.details_layout.addWidget(payment_box)

        # Reprint Invoice PDF Button
        self.reprint_button = AnimatedButton("إعادة طباعة الفاتورة 🧾")
        self.reprint_button.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
        """)
        self.reprint_button.clicked.connect(self.reprint_invoice)
        self.details_layout.addWidget(self.reprint_button)

        columns.addWidget(right, 2)

        self.search()

    def search(self):
        self._offset = 0
        query = self.search_edit.text().strip()
        self.visits = visit_service.search_visits(query, self.unpaid_check.isChecked(), limit=self._limit, offset=self._offset)
        self._populate_visits_table()

    def load_more(self):
        self._offset += self._limit
        query = self.search_edit.text().strip()
        more = visit_service.search_visits(query, self.unpaid_check.isChecked(), limit=self._limit, offset=self._offset)
        if not more:
            return
        self.visits.extend(more)
        self._populate_visits_table()

    def _populate_visits_table(self):
        self.visits_table.setRowCount(len(self.visits))
        for row, v in enumerate(self.visits):
            raw_date = (v.get("visit_date") or "")[:16].replace("T", " ")

            item_inv = QTableWidgetItem(str(v["invoice_number"]))
            item_pat = QTableWidgetItem(v["patient_name"])
            item_date = QTableWidgetItem(raw_date)
            item_tot = QTableWidgetItem(f"{v['total_amount']:.2f}")
            item_paid = QTableWidgetItem(f"{v['paid_amount']:.2f}")

            bal = v["balance"]
            item_bal = QTableWidgetItem(f"{bal:.2f}")
            if bal > 0.01:
                item_bal.setForeground(QColor("#EF4444"))
            else:
                item_bal.setForeground(QColor("#10B981"))

            for item in (item_inv, item_pat, item_date, item_tot, item_paid, item_bal):
                item.setTextAlignment(Qt.AlignCenter)

            self.visits_table.setItem(row, 0, item_inv)
            self.visits_table.setItem(row, 1, item_pat)
            self.visits_table.setItem(row, 2, item_date)
            self.visits_table.setItem(row, 3, item_tot)
            self.visits_table.setItem(row, 4, item_paid)
            self.visits_table.setItem(row, 5, item_bal)

    def on_select_visit_row(self):
        selected_rows = self.visits_table.selectionModel().selectedRows()
        if not selected_rows:
            self._clear_details()
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.visits):
            self._clear_details()
            return

        self.selected_visit_id = self.visits[row]["id"]
        details = visit_service.get_visit_details(self.selected_visit_id)
        raw_date = (details.get("visit_date") or "")[:16].replace("T", " ")

        self.details_title.setText(f"تفاصيل الفاتورة رقم {details['invoice_number']}")
        self.lbl_patient.setText(f"<b>👤 المريض:</b> {details['patient_name']}")
        self.lbl_date_time.setText(f"<b>📅 التاريخ والوقت:</b> {raw_date}")
        self.lbl_total.setText(f"<b>💰 الإجمالي:</b> {details['total_amount']:.2f} ج.م")
        self.lbl_discount.setText(f"<b>🏷️ الخصم:</b> {details['discount_amount']:.2f} ج.م")
        self.lbl_paid.setText(f"<b>💵 المدفوع:</b> {details['paid_amount']:.2f} ج.م")

        bal = details['balance']
        bal_color = "#EF4444" if bal > 0.01 else "#10B981"
        self.lbl_balance.setText(f"<b>⚠️ المتبقي:</b> <font color='{bal_color}'>{bal:.2f} ج.م</font>")

        orders = details.get("orders", [])
        self.tests_table.setRowCount(len(orders))
        for r_i, o in enumerate(orders):
            status_display = STATUS_LABELS.get(o["status"], o["status"])
            item_t = QTableWidgetItem(o["test_name"])
            item_p = QTableWidgetItem(f"{o['price']:.2f}")
            item_s = QTableWidgetItem(status_display)

            for item in (item_t, item_p, item_s):
                item.setTextAlignment(Qt.AlignCenter)

            self.tests_table.setItem(r_i, 0, item_t)
            self.tests_table.setItem(r_i, 1, item_p)
            self.tests_table.setItem(r_i, 2, item_s)

    def _clear_details(self):
        self.selected_visit_id = None
        self.details_title.setText("اختر فاتورة من الجدول لعرض تفاصيلها")
        self.lbl_patient.setText("<b>👤 المريض:</b> -")
        self.lbl_date_time.setText("<b>📅 التاريخ:</b> -")
        self.lbl_total.setText("<b>💰 الإجمالي:</b> -")
        self.lbl_discount.setText("<b>🏷️ الخصم:</b> -")
        self.lbl_paid.setText("<b>💵 المدفوع:</b> -")
        self.lbl_balance.setText("<b>⚠️ المتبقي:</b> -")
        self.tests_table.setRowCount(0)

    def add_payment(self):
        if self.selected_visit_id is None:
            QMessageBox.warning(self, "تنبيه", "رجاءً اختر زيارة من الجدول أولاً.")
            return
        val = self.payment_spin.value()
        if val <= 0:
            QMessageBox.warning(self, "تنبيه", "أدخل مبلغ دفعة أكبر من صفر.")
            return

        visit_service.add_payment(self.selected_visit_id, val)
        self.payment_spin.setValue(0)
        self.search()
        self.on_select_visit_row()
        QMessageBox.information(self, "تم التسجيل", f"تم تسجيل الدفعة بقيمة {val:.2f} ج.م بنجاح!")

    def reprint_invoice(self):
        if self.selected_visit_id is None:
            QMessageBox.warning(self, "تنبيه", "رجاءً اختر زيارة من الجدول أولاً.")
            return

        details = visit_service.get_visit_details(self.selected_visit_id)
        settings = catalog_service.get_lab_settings()
        try:
            path = generate_invoice_pdf(details, details["orders"], settings)
            self._open_file(path)
            QMessageBox.information(
                self, "✅ تم طباعة الفاتورة",
                f"تم توليد وفتح الفاتورة رقم {details['invoice_number']} بنجاح!\n\n📁 مسار الحفظ:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "خطأ بالطباعة", f"تعذر إعادة طباعة الفاتورة: {exc}")

    def _open_file(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
