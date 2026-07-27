import csv
import os

from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor, QPainter
from PySide2.QtWidgets import (QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
                                QLabel, QListWidget, QMessageBox, QPushButton, QTableWidget,
                                QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView)
from PySide2.QtCharts import QtCharts

from app.config import BACKUPS_DIR
from app.ui.styles import get_saved_theme
from app.ui.widgets import HintBanner
from app.services import result_service, visit_service
from app.services.result_service import STATUS_LABELS


class StatCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, icon_str: str = "📊", accent_color: str = "#146C8E", tooltip: str = ""):
        super().__init__()
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)

        self.accent_color = accent_color
        self.setStyleSheet(f"""
            QFrame#Card {{
                border-right: 5px solid {accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)

        header_layout = QHBoxLayout()
        icon_label = QLabel(icon_str)
        icon_label.setStyleSheet("font-size: 18px;")
        header_layout.addWidget(icon_label)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {accent_color}; margin-top: 4px;")
        layout.addWidget(self.value_label)

        hint = QLabel("اضغط للتفاصيل 🠄")
        hint.setStyleSheet("color: #9CA3AF; font-size: 10px;")
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
        self.resize(580, 440)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: bold; font-size: 14px; color: #146C8E;")
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
        self.days_filter = 7

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header Title & Filter Bar
        header_row = QHBoxLayout()
        title = QLabel("لوحة المتابعة والتحليلات")
        title.setObjectName("PageTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        # Period Combo Filter
        self.period_combo = QComboBox()
        self.period_combo.addItems(["آخر 7 أيام", "آخر 30 يوماً"])
        self.period_combo.setFixedWidth(140)
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        header_row.addWidget(self.period_combo)

        # Refresh & Export Buttons
        refresh_button = QPushButton("تحديث 🔄")
        refresh_button.setObjectName("Primary")
        refresh_button.clicked.connect(self.refresh)
        header_row.addWidget(refresh_button)

        export_button = QPushButton("تصدير CSV 📊")
        export_button.clicked.connect(self.export_summary)
        header_row.addWidget(export_button)

        layout.addLayout(header_row)

        layout.addWidget(HintBanner(
            "تحليلات وإحصائيات المعمل اللحظية. اضغط على أي بطاقة لعرض التفاصيل الكاملة، أو تابع الحركة والرسوم البيانية أدناه."
        ))

        # Top 4 Hero Cards
        grid = QGridLayout()
        grid.setSpacing(10)

        self.visits_card = StatCard("زيارات اليوم", "📅", "#0284C7", "عدد الزيارات المسجَّلة اليوم")
        self.revenue_card = StatCard("إيرادات اليوم", "💰", "#10B981", "إجمالي الدفعات المُسجَّلة اليوم")
        self.pending_card = StatCard("نتائج قيد الانتظار", "⏳", "#F59E0B", "تحاليل بانتظار كتابة النتائج أو الاعتماد")
        self.outstanding_card = StatCard("مبالغ متبقية", "⚠️", "#EF4444", "إجمالي المبالغ المستحقة على الزيارات غير المسددة")

        grid.addWidget(self.visits_card, 0, 0)
        grid.addWidget(self.revenue_card, 0, 1)
        grid.addWidget(self.pending_card, 0, 2)
        grid.addWidget(self.outstanding_card, 0, 3)

        layout.addLayout(grid)

        # Connect Card Signals
        self.visits_card.clicked.connect(self.show_todays_visits)
        self.revenue_card.clicked.connect(self.show_todays_revenue)
        self.pending_card.clicked.connect(self.show_pending_results)
        self.outstanding_card.clicked.connect(self.show_outstanding)

        # Middle Section: Interactive Charts
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(12)

        # Chart 1: Revenue & Visits Trend
        self.trend_chart_view = QtCharts.QChartView()
        self.trend_chart_view.setRenderHint(QPainter.Antialiasing)
        self.trend_chart_view.setMinimumHeight(240)
        charts_layout.addWidget(self.trend_chart_view, 2)

        # Chart 2: Top Requested Tests
        self.tests_chart_view = QtCharts.QChartView()
        self.tests_chart_view.setRenderHint(QPainter.Antialiasing)
        self.tests_chart_view.setMinimumHeight(240)
        charts_layout.addWidget(self.tests_chart_view, 1)

        layout.addLayout(charts_layout)

        # Bottom Section: Recent Visits Table
        recent_header = QHBoxLayout()
        recent_label = QLabel("أحدث زيارات اليوم")
        recent_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        recent_header.addWidget(recent_label)
        recent_header.addStretch()
        layout.addLayout(recent_header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["رقم الفاتورة", "اسم المريض", "الإجمالي", "المدفوع", "المتبقي"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(140)
        layout.addWidget(self.table)

        self.refresh()

    def on_period_changed(self, index):
        self.days_filter = 7 if index == 0 else 30
        self.refresh()

    def refresh(self):
        snap = visit_service.dashboard_snapshot()
        self.visits_card.set_value(str(snap["visits_today"]))
        self.revenue_card.set_value(f"{snap['revenue_today']:.2f} ج.م")
        self.pending_card.set_value(str(snap["pending_results"]))
        self.outstanding_card.set_value(f"{snap['outstanding']:.2f} ج.م")

        self.build_trend_chart()
        self.build_top_tests_chart()
        self.populate_recent_visits()

    def build_trend_chart(self):
        trends = visit_service.get_daily_trends(self.days_filter)
        chart = QtCharts.QChart()
        chart.setTitle(f"نمو الإيرادات والزيارات (آخر {self.days_filter} أيام)")
        chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        bar_set = QtCharts.QBarSet("الزيارات")
        bar_set.setColor(QColor("#0284C7"))

        line_series = QtCharts.QLineSeries()
        line_series.setName("الإيرادات (ج.م)")
        pen = line_series.pen()
        pen.setColor(QColor("#10B981"))
        pen.setWidth(3)
        line_series.setPen(pen)

        categories = []
        max_rev = 10.0
        for i, t in enumerate(trends):
            bar_set.append(t["visits"])
            line_series.append(i, t["revenue"])
            categories.append(t["date"])
            if t["revenue"] > max_rev:
                max_rev = t["revenue"]

        bar_series = QtCharts.QBarSeries()
        bar_series.append(bar_set)

        chart.addSeries(bar_series)
        chart.addSeries(line_series)

        axis_x = QtCharts.QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)

        axis_y = QtCharts.QValueAxis()
        axis_y.setRange(0, max_rev * 1.15)
        axis_y.setTitleText("الإيراد (ج.م)")
        chart.addAxis(axis_y, Qt.AlignLeft)
        line_series.attachAxis(axis_y)

        is_dark = get_saved_theme() == "dark"
        chart.setTheme(QtCharts.QChart.ChartThemeDark if is_dark else QtCharts.QChart.ChartThemeLight)
        self.trend_chart_view.setChart(chart)

    def build_top_tests_chart(self):
        top_tests = visit_service.get_top_requested_tests(5)
        chart = QtCharts.QChart()
        chart.setTitle("أكثر التحاليل طلباً")
        chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        series = QtCharts.QPieSeries()
        colors = ["#0284C7", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"]

        for idx, t in enumerate(top_tests):
            slice_item = series.append(f"{t['test_name']} ({t['count']})", t['count'])
            slice_item.setColor(QColor(colors[idx % len(colors)]))
            if idx == 0:
                slice_item.setExploded(True)
                slice_item.setLabelVisible(True)

        chart.addSeries(series)
        chart.legend().setAlignment(Qt.AlignBottom)

        is_dark = get_saved_theme() == "dark"
        chart.setTheme(QtCharts.QChart.ChartThemeDark if is_dark else QtCharts.QChart.ChartThemeLight)
        self.tests_chart_view.setChart(chart)

    def populate_recent_visits(self):
        visits = visit_service.get_todays_visits()
        self.table.setRowCount(len(visits))
        for row, v in enumerate(visits):
            self.table.setItem(row, 0, QTableWidgetItem(str(v["invoice_number"])))
            self.table.setItem(row, 1, QTableWidgetItem(v["patient_name"]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{v['total_amount']:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{v['paid_amount']:.2f}"))
            bal = v['total_amount'] - v['paid_amount']
            item_bal = QTableWidgetItem(f"{bal:.2f}")
            if bal > 0.01:
                item_bal.setForeground(QColor("#EF4444"))
            self.table.setItem(row, 4, item_bal)

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
