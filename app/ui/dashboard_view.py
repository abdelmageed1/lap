import csv
import os

from PySide2.QtCore import Qt, Signal
from PySide2.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
                                QMessageBox, QPushButton, QVBoxLayout, QWidget)

from app.config import BACKUPS_DIR

from app.ui.widgets import HintBanner

from app.services import result_service, visit_service
from app.services.result_service import STATUS_LABELS


class StatCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, tooltip: str = ""):
        super().__init__()
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0B4F6C;")
        hint = QLabel("اضغط لعرض التفاصيل")
        hint.setStyleSheet("color: #9CA3AF; font-size: 10px;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(hint)

    def set_value(self, text: str):
        self.value_label.setText(text)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class DetailDialog(QDialog):
    def __init__(self, title: str, lines: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: bold; color: #0B4F6C; font-size: 13px;")
        layout.addWidget(heading)
        listw = QListWidget()
        if lines:
            listw.addItems(lines)
        else:
            listw.addItem("لا توجد بيانات لعرضها")
        layout.addWidget(listw)
        close_button = QPushButton("إغلاق")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("لوحة المتابعة")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(HintBanner(
            "نظرة سريعة على نشاط اليوم. اضغط على أي بطاقة لعرض تفاصيلها الكاملة (قائمة الزيارات، "
            "الدفعات، أو التحاليل نفسها)."
        ))

        grid = QGridLayout()
        grid.setSpacing(12)
        self.visits_card = StatCard("زيارات اليوم", "عدد الزيارات المسجَّلة اليوم - اضغط لعرض قائمتها")
        self.revenue_card = StatCard("إيرادات اليوم", "إجمالي الدفعات المُسجَّلة اليوم - اضغط لعرض تفاصيلها")
        self.week_card = StatCard("أسبوع", "إجمالي الزيارات والإيرادات خلال آخر 7 أيام")
        self.month_card = StatCard("شهر", "إجمالي الزيارات والإيرادات خلال هذا الشهر")
        self.outstanding_card = StatCard("مبالغ متبقية", "كل الزيارات التي لم تُسدَّد بالكامل بعد")
        self.pending_card = StatCard("نتائج قيد الانتظار", "تحاليل لم تُعتمَد نتيجتها بعد (إدخال أو مراجعة)")
        self.patients_card = StatCard("إجمالي المرضى", "كل المرضى المسجَّلين في النظام، الأحدث أولًا")
        grid.addWidget(self.visits_card, 0, 0)
        grid.addWidget(self.revenue_card, 0, 1)
        grid.addWidget(self.week_card, 0, 2)
        grid.addWidget(self.month_card, 0, 3)
        grid.addWidget(self.outstanding_card, 1, 0)
        grid.addWidget(self.pending_card, 1, 1)
        grid.addWidget(self.patients_card, 1, 2)
        layout.addLayout(grid)

        self.visits_card.clicked.connect(self.show_todays_visits)
        self.revenue_card.clicked.connect(self.show_todays_revenue)
        self.week_card.clicked.connect(self.show_week_summary)
        self.month_card.clicked.connect(self.show_month_summary)
        self.outstanding_card.clicked.connect(self.show_outstanding)
        self.pending_card.clicked.connect(self.show_pending_results)
        self.patients_card.clicked.connect(self.show_recent_patients)

        buttons_row = QHBoxLayout()
        refresh_button = QPushButton("تحديث")
        refresh_button.setObjectName("Primary")
        refresh_button.setToolTip("تحديث الأرقام لتعكس آخر الزيارات والدفعات")
        refresh_button.setFixedWidth(100)
        refresh_button.clicked.connect(self.refresh)
        buttons_row.addWidget(refresh_button)

        export_button = QPushButton("تصدير ملخص")
        export_button.setToolTip("تصدير ملخص لوحة المتابعة إلى ملف CSV")
        export_button.clicked.connect(self.export_summary)
        buttons_row.addWidget(export_button)
        layout.addLayout(buttons_row)
        layout.addStretch()

        self.refresh()

    def refresh(self):
        snap = visit_service.dashboard_snapshot()
        self.visits_card.set_value(str(snap["visits_today"]))
        self.revenue_card.set_value(f"{snap['revenue_today']:.2f}")
        self.week_card.set_value(f"{snap['visits_week']} / {snap['revenue_week']:.2f}")
        self.month_card.set_value(f"{snap['visits_month']} / {snap['revenue_month']:.2f}")
        self.outstanding_card.set_value(f"{snap['outstanding']:.2f}")
        self.pending_card.set_value(str(snap["pending_results"]))
        self.patients_card.set_value(str(snap["total_patients"]))

    def export_summary(self):
        snap = visit_service.dashboard_snapshot()
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        path = os.path.join(BACKUPS_DIR, "dashboard_summary.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["المؤشر", "القيمة"])
            writer.writerow(["زيارات اليوم", snap["visits_today"]])
            writer.writerow(["إيرادات اليوم", f"{snap['revenue_today']:.2f}"])
            writer.writerow(["زيارات آخر 7 أيام", snap["visits_week"]])
            writer.writerow(["إيرادات آخر 7 أيام", f"{snap['revenue_week']:.2f}"])
            writer.writerow(["زيارات هذا الشهر", snap["visits_month"]])
            writer.writerow(["إيرادات هذا الشهر", f"{snap['revenue_month']:.2f}"])
            writer.writerow(["مبالغ متبقية", f"{snap['outstanding']:.2f}"])
            writer.writerow(["نتائج قيد الانتظار", snap["pending_results"]])
            writer.writerow(["إجمالي المرضى", snap["total_patients"]])
        QMessageBox.information(self, "تم التصدير", f"تم حفظ الملخص في:\n{path}")

    def show_todays_visits(self):
        visits = visit_service.get_todays_visits()
        lines = [
            f"فاتورة {v['invoice_number']} - {v['patient_name']} - "
            f"الإجمالي {v['total_amount']:.2f} - المدفوع {v['paid_amount']:.2f}"
            for v in visits
        ]
        DetailDialog("زيارات اليوم", lines, parent=self).exec_()

    def show_todays_revenue(self):
        payments = visit_service.get_todays_payments()
        lines = [
            f"فاتورة {p['invoice_number']} - {p['patient_name']} - دفعة {p['amount']:.2f} - {p['paid_at'][11:16]}"
            for p in payments
        ]
        DetailDialog("إيرادات اليوم (الدفعات المُسجَّلة)", lines, parent=self).exec_()

    def show_week_summary(self):
        snap = visit_service.dashboard_snapshot()
        lines = [
            f"الزيارات خلال آخر 7 أيام: {snap['visits_week']}",
            f"الإيرادات خلال آخر 7 أيام: {snap['revenue_week']:.2f}",
        ]
        DetailDialog("ملخص الأسبوع", lines, parent=self).exec_()

    def show_month_summary(self):
        snap = visit_service.dashboard_snapshot()
        lines = [
            f"الزيارات هذا الشهر: {snap['visits_month']}",
            f"الإيرادات هذا الشهر: {snap['revenue_month']:.2f}",
        ]
        DetailDialog("ملخص الشهر", lines, parent=self).exec_()

    def show_outstanding(self):
        visits = visit_service.get_outstanding_visits()
        lines = [
            f"فاتورة {v['invoice_number']} - {v['patient_name']} - المتبقي {v['balance']:.2f}"
            for v in visits
        ]
        DetailDialog("زيارات بمبالغ متبقية", lines, parent=self).exec_()

    def show_pending_results(self):
        entry = result_service.get_pending_orders(limit=500)
        review = result_service.get_orders_pending_review(limit=500)
        lines = [f"{o['test_name']} - {o['patient_name']} - {STATUS_LABELS.get('InProgress')}" for o in entry]
        lines += [f"{o['test_name']} - {o['patient_name']} - {STATUS_LABELS.get('Completed')}" for o in review]
        DetailDialog("نتائج قيد الانتظار", lines, parent=self).exec_()

    def show_recent_patients(self):
        patients = visit_service.get_recent_patients()
        lines = [
            f"{p['full_name']} - {p.get('phone') or '-'} - {p['visit_count']} زيارة"
            for p in patients
        ]
        DetailDialog("المرضى (الأحدث أولًا)", lines, parent=self).exec_()
