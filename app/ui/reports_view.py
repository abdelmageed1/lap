import csv
import os
from PySide2.QtCore import QDate, Qt
from PySide2.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QFileDialog, QFrame, QGridLayout,
                                QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
                                QScrollArea, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


from app.services import reports_service
from app.ui.animated_button import AnimatedButton
from app.ui.dashboard_table_dialog import DashboardVisitsTableDialog
from app.ui.reports_chart_widgets import KPICardWidget, BarChartWidget
from app.ui.styles import get_color
from app.ui.widgets import HintBanner


class ReportsView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        self.selected_doctor_id = None
        self.selected_doctor_name = ""
        self.selected_staff_id = None
        self.selected_staff_name = ""

        outer = QVBoxLayout(self)
        title = QLabel("التقارير والإحصائيات والتحليلات البيانية")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "تتيح لك هذه الشاشة تحليل أداء المعمل بيانيًا، وعرض أداء الأطباء المحولين ومتابعة إنتاجية الموظفين "
            "مع إمكانية التصدير إلى Excel/CSV."
        ))

        # KPI Cards Summary Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)

        self.kpi_revenue = KPICardWidget("إجمالي الإيرادات", "0.00 ج.م", "💰", bg_color="#0F766E")
        self.kpi_visits = KPICardWidget("إجمالي عدد الزيارات", "0 زيارة", "📋", bg_color="#0284C7")
        self.kpi_paid = KPICardWidget("صافي التحصيلات", "0.00 ج.م", "💵", bg_color="#166534")
        self.kpi_balance = KPICardWidget("إجمالي المتبقي", "0.00 ج.م", "⚖️", bg_color="#B91C1C")

        self.kpi_revenue.clicked.connect(lambda: self._show_kpi_drilldown("💰 تفاصيل إجمالي الإيرادات"))
        self.kpi_visits.clicked.connect(lambda: self._show_kpi_drilldown("📋 تفاصيل الزيارات"))
        self.kpi_paid.clicked.connect(lambda: self._show_kpi_drilldown("💵 تفاصيل صافي التحصيلات"))
        self.kpi_balance.clicked.connect(lambda: self._show_kpi_drilldown("⚖️ تفاصيل المبالغ المتبقية", only_outstanding=True))

        kpi_row.addWidget(self.kpi_revenue)
        kpi_row.addWidget(self.kpi_visits)
        kpi_row.addWidget(self.kpi_paid)
        kpi_row.addWidget(self.kpi_balance)
        outer.addLayout(kpi_row)

        # Filter bar
        filter_card = QFrame()
        filter_card.setObjectName("Card")
        filter_layout = QHBoxLayout(filter_card)

        filter_layout.addWidget(QLabel("<b>الفترة:</b>"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["الكل", "اليوم", "هذا الأسبوع", "هذا الشهر", "هذا العام"])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        filter_layout.addWidget(self.preset_combo)

        self.use_date_filter = QCheckBox("تفعيل النطاق الزمني")
        self.use_date_filter.toggled.connect(self.on_date_filter_toggled)
        filter_layout.addWidget(self.use_date_filter)

        filter_layout.addWidget(QLabel("من:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setEnabled(False)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("إلى:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setEnabled(False)
        filter_layout.addWidget(self.date_to)

        self.btn_refresh = AnimatedButton("تحديث البيانات 🔄")
        self.btn_refresh.clicked.connect(self.refresh_all_reports)
        filter_layout.addWidget(self.btn_refresh)

        self.btn_export = AnimatedButton("تصدير إلى CSV 📊")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #0D9488;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
        """)
        self.btn_export.clicked.connect(self.export_current_tab_csv)
        filter_layout.addWidget(self.btn_export)

        filter_layout.addStretch()
        outer.addWidget(filter_card)

        # Tabs container
        self.tabs = QTabWidget()
        self.tab_doctors = self._build_doctors_tab()
        self.tab_sources = self._build_sources_tab()
        self.tab_departments = self._build_departments_tab()
        self.tab_staff = self._build_staff_tab()
        self.tab_charts = self._build_charts_dash_tab()

        self.tabs.addTab(self.tab_doctors, "🩺 الأطباء والمرضى المحولون")
        self.tabs.addTab(self.tab_sources, "🏢 جهات الإحالة والتعاقدات")
        self.tabs.addTab(self.tab_departments, "🧪 إحصائيات الأقسام الطبية")
        self.tabs.addTab(self.tab_staff, "👥 إنتاجية موظفي المعمل")
        self.tabs.addTab(self.tab_charts, "📊 الرسوم والتحليلات البيانية")



        outer.addWidget(self.tabs)
        self.refresh_all_reports()

    def _show_kpi_drilldown(self, title: str, only_outstanding: bool = False):
        start_date, end_date = self._get_dates()
        visits = reports_service.get_visits_in_range(start_date=start_date, end_date=end_date,
                                                       only_outstanding=only_outstanding)
        DashboardVisitsTableDialog(title, visits, parent=self).exec_()

    def on_preset_changed(self, index):
        preset = self.preset_combo.currentText()
        today = QDate.currentDate()
        if preset == "الكل":
            self.use_date_filter.setChecked(False)
        elif preset == "اليوم":
            self.use_date_filter.setChecked(True)
            self.date_from.setDate(today)
            self.date_to.setDate(today)
        elif preset == "هذا الأسبوع":
            self.use_date_filter.setChecked(True)
            self.date_from.setDate(today.addDays(-7))
            self.date_to.setDate(today)
        elif preset == "هذا الشهر":
            self.use_date_filter.setChecked(True)
            self.date_from.setDate(QDate(today.year(), today.month(), 1))
            self.date_to.setDate(today)
        elif preset == "هذا العام":
            self.use_date_filter.setChecked(True)
            self.date_from.setDate(QDate(today.year(), 1, 1))
            self.date_to.setDate(today)
        self.refresh_all_reports()

    def on_date_filter_toggled(self, checked):
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)
        self.refresh_all_reports()

    def _get_dates(self):
        if not self.use_date_filter.isChecked():
            return None, None
        return self.date_from.date().toString("yyyy-MM-dd"), self.date_to.date().toString("yyyy-MM-dd")

    # ==================== Doctors & Patient Drilldown Tab ====================
    def _build_doctors_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        splitter = QSplitter(Qt.Vertical)

        # Upper frame: Doctors summary
        doc_card = QFrame()
        doc_card.setObjectName("Card")
        doc_layout = QVBoxLayout(doc_card)
        doc_layout.addWidget(QLabel("<b>قائمة الأطباء المحولين وإجمالي الإيرادات (اضغط على طبيب للتعمق في مرضاؤه):</b>"))

        self.doctors_table = QTableWidget()
        self.doctors_table.setColumnCount(7)
        self.doctors_table.setHorizontalHeaderLabels([
            "م", "اسم الطبيب", "عدد الزيارات", "إجمالي المبالغ", "الخصومات", "المدفوع", "المتبقي"
        ])
        self.doctors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doctors_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.doctors_table.setSelectionMode(QTableWidget.SingleSelection)
        self.doctors_table.itemSelectionChanged.connect(self.on_doctor_selected)
        doc_layout.addWidget(self.doctors_table)
        splitter.addWidget(doc_card)

        # Lower frame: Patient Drilldown table for selected doctor
        patient_card = QFrame()
        patient_card.setObjectName("Card")
        patient_layout = QVBoxLayout(patient_card)
        self.lbl_doctor_drilldown_title = QLabel("<b>📋 تفاصيل المرضى المحولين:</b> (اختر طبيبًا من الجدول أعلى)")
        self.lbl_doctor_drilldown_title.setStyleSheet(f"color: {get_color('primary_text')}; font-size: 13px;")
        patient_layout.addWidget(self.lbl_doctor_drilldown_title)

        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(8)
        self.patients_table.setHorizontalHeaderLabels([
            "رقم الفاتورة", "اسم المريض", "رقم التليفون", "تاريخ الزيارة", "التحاليل المطلوبة", "الإجمالي", "المدفوع", "المتبقي"
        ])
        self.patients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        patient_layout.addWidget(self.patients_table)
        splitter.addWidget(patient_card)

        splitter.setSizes([300, 350])
        layout.addWidget(splitter)
        return widget

    # ==================== Referral Sources Tab ====================
    def _build_sources_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("<b>تقرير الإيرادات حسب جهة الإحالة والتعاقدات:</b>"))

        self.sources_table = QTableWidget()
        self.sources_table.setColumnCount(6)
        self.sources_table.setHorizontalHeaderLabels([
            "جهة الإحالة / التعاقد", "عدد الزيارات", "إجمالي المبالغ", "الخصومات", "المدفوع الصافي", "المتبقي"
        ])
        self.sources_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        card_layout.addWidget(self.sources_table)
        layout.addWidget(card)
        return widget

    # ==================== Department Revenue Tab ====================
    def _build_departments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel("<b>توزيع طلبات التحاليل والإيراد حسب الأقسام الطبية:</b>"))

        self.departments_table = QTableWidget()
        self.departments_table.setColumnCount(3)
        self.departments_table.setHorizontalHeaderLabels([
            "القسم الطبي", "عدد الطلبات / التحاليل", "إجمالي الإيرادات"
        ])
        self.departments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        card_layout.addWidget(self.departments_table)
        layout.addWidget(card)
        return widget

    # ==================== Staff Performance Analytics Tab ====================
    def _build_staff_tab(self):

        widget = QWidget()
        layout = QVBoxLayout(widget)

        splitter = QSplitter(Qt.Vertical)

        # Upper frame: Staff overview table
        staff_card = QFrame()
        staff_card.setObjectName("Card")
        staff_layout = QVBoxLayout(staff_card)
        staff_layout.addWidget(QLabel("<b>إنتاجية وأداء موظفي المعمل (اضغط على موظف للتعمق في مرضاه وزياراته):</b>"))

        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(8)
        self.staff_table.setHorizontalHeaderLabels([
            "م", "اسم الموظف", "اسم الحساب", "الدور الوظيفي", "المرضى المسجلون", "الفواتير المنشأة", "إجمالي التحصيلات", "النتائج المعالجة"
        ])
        self.staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.staff_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.staff_table.setSelectionMode(QTableWidget.SingleSelection)
        self.staff_table.itemSelectionChanged.connect(self.on_staff_selected)
        staff_layout.addWidget(self.staff_table)
        splitter.addWidget(staff_card)

        # Lower frame: Patients/Visits handled by selected staff member
        drilldown_card = QFrame()
        drilldown_card.setObjectName("Card")
        drilldown_layout = QVBoxLayout(drilldown_card)
        self.lbl_staff_drilldown_title = QLabel("<b>📋 سجل عمليات الموظف:</b> (اختر موظفًا من الجدول أعلى)")
        self.lbl_staff_drilldown_title.setStyleSheet(f"color: {get_color('primary_text')}; font-size: 13px;")
        drilldown_layout.addWidget(self.lbl_staff_drilldown_title)

        self.staff_patients_table = QTableWidget()
        self.staff_patients_table.setColumnCount(8)
        self.staff_patients_table.setHorizontalHeaderLabels([
            "رقم الفاتورة", "اسم المريض", "رقم التليفون", "تاريخ الزيارة", "التحاليل المطلوبة", "الإجمالي", "المدفوع", "المتبقي"
        ])
        self.staff_patients_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        drilldown_layout.addWidget(self.staff_patients_table)
        splitter.addWidget(drilldown_card)

        splitter.setSizes([300, 350])
        layout.addWidget(splitter)
        return widget

    # ==================== Graphical Analytics Dashboard Tab ====================
    def _build_charts_dash_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        grid = QGridLayout(scroll_content)
        grid.setSpacing(16)

        self.chart_doctors = BarChartWidget("🩺 أعلى الأطباء تحويلاً للمرضى (حسب الإيرادات):")
        self.chart_departments = BarChartWidget("🧪 توزيع إيرادات الأقسام الطبية:")
        self.chart_sources = BarChartWidget("🏢 توزيع فواتير وإيرادات جهات الإحالة والتعاقدات:")
        self.chart_staff = BarChartWidget("👥 مقارنة إنتاجية الموظفين (تسجيل المرضى والمعالجة):")

        card1 = QFrame(); card1.setObjectName("Card")
        l1 = QVBoxLayout(card1); l1.addWidget(self.chart_doctors)
        grid.addWidget(card1, 0, 0)

        card2 = QFrame(); card2.setObjectName("Card")
        l2 = QVBoxLayout(card2); l2.addWidget(self.chart_departments)
        grid.addWidget(card2, 0, 1)

        card3 = QFrame(); card3.setObjectName("Card")
        l3 = QVBoxLayout(card3); l3.addWidget(self.chart_sources)
        grid.addWidget(card3, 1, 0)

        card4 = QFrame(); card4.setObjectName("Card")
        l4 = QVBoxLayout(card4); l4.addWidget(self.chart_staff)
        grid.addWidget(card4, 1, 1)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return widget

    # ==================== Data Loading & Refresh ====================
    def refresh_all_reports(self):
        start_date, end_date = self._get_dates()

        # 1. Refresh Doctors Table
        self.doctors_data = reports_service.get_top_referring_doctors(start_date=start_date, end_date=end_date)
        self.doctors_table.setRowCount(len(self.doctors_data))
        for row_idx, doc in enumerate(self.doctors_data):
            self.doctors_table.setItem(row_idx, 0, QTableWidgetItem(str(doc["doctor_id"])))
            self.doctors_table.setItem(row_idx, 1, QTableWidgetItem(doc["doctor_name"] or "غير محدد"))
            self.doctors_table.setItem(row_idx, 2, QTableWidgetItem(str(doc["visit_count"])))
            self.doctors_table.setItem(row_idx, 3, QTableWidgetItem(f"{doc['total_amount']:.2f}"))
            self.doctors_table.setItem(row_idx, 4, QTableWidgetItem(f"{doc['total_discount']:.2f}"))
            self.doctors_table.setItem(row_idx, 5, QTableWidgetItem(f"{doc['total_paid']:.2f}"))
            self.doctors_table.setItem(row_idx, 6, QTableWidgetItem(f"{doc['total_balance']:.2f}"))

        if self.selected_doctor_id is not None:
            self.load_doctor_patients(self.selected_doctor_id, self.selected_doctor_name)
        else:
            self.patients_table.setRowCount(0)
            self.lbl_doctor_drilldown_title.setText("<b>📋 تفاصيل المرضى المحولين:</b> (اختر طبيبًا من الجدول أعلى)")

        # 2. Refresh Sources Table
        self.sources_data = reports_service.get_referral_sources_analytics(start_date=start_date, end_date=end_date)
        self.sources_table.setRowCount(len(self.sources_data))
        for row_idx, src in enumerate(self.sources_data):
            self.sources_table.setItem(row_idx, 0, QTableWidgetItem(src["source_name"]))
            self.sources_table.setItem(row_idx, 1, QTableWidgetItem(str(src["visit_count"])))
            self.sources_table.setItem(row_idx, 2, QTableWidgetItem(f"{src['total_amount']:.2f}"))
            self.sources_table.setItem(row_idx, 3, QTableWidgetItem(f"{src['total_discount']:.2f}"))
            self.sources_table.setItem(row_idx, 4, QTableWidgetItem(f"{src['total_paid']:.2f}"))
            self.sources_table.setItem(row_idx, 5, QTableWidgetItem(f"{src['total_balance']:.2f}"))

        # 3. Refresh Departments Table
        self.departments_data = reports_service.get_department_revenue_breakdown(start_date=start_date, end_date=end_date)
        self.departments_table.setRowCount(len(self.departments_data))
        for row_idx, dep in enumerate(self.departments_data):
            self.departments_table.setItem(row_idx, 0, QTableWidgetItem(dep["department_name"]))
            self.departments_table.setItem(row_idx, 1, QTableWidgetItem(str(dep["order_count"])))
            self.departments_table.setItem(row_idx, 2, QTableWidgetItem(f"{dep['total_revenue']:.2f}"))

        # 4. Refresh Staff Table
        self.staff_data = reports_service.get_staff_productivity_analytics(start_date=start_date, end_date=end_date)
        self.staff_table.setRowCount(len(self.staff_data))
        for row_idx, st in enumerate(self.staff_data):
            self.staff_table.setItem(row_idx, 0, QTableWidgetItem(str(st["user_id"])))
            self.staff_table.setItem(row_idx, 1, QTableWidgetItem(st["full_name"]))
            self.staff_table.setItem(row_idx, 2, QTableWidgetItem(st["username"]))
            self.staff_table.setItem(row_idx, 3, QTableWidgetItem(st["role_name"]))
            self.staff_table.setItem(row_idx, 4, QTableWidgetItem(str(st["registered_patients"])))
            self.staff_table.setItem(row_idx, 5, QTableWidgetItem(str(st["visits_created"])))
            self.staff_table.setItem(row_idx, 6, QTableWidgetItem(f"{st['collected_payments']:.2f}"))
            self.staff_table.setItem(row_idx, 7, QTableWidgetItem(str(st["results_processed"])))

        if self.selected_staff_id is not None:
            self.load_staff_patients(self.selected_staff_id, self.selected_staff_name)
        else:
            self.staff_patients_table.setRowCount(0)
            self.lbl_staff_drilldown_title.setText("<b>📋 سجل عمليات الموظف:</b> (اختر موظفًا من الجدول أعلى)")

        # 5. Update KPI Cards Summary Totals
        tot_rev = sum([s["total_amount"] for s in self.sources_data]) if self.sources_data else sum([d["total_amount"] for d in self.doctors_data])
        tot_vis = sum([s["visit_count"] for s in self.sources_data]) if self.sources_data else sum([d["visit_count"] for d in self.doctors_data])
        tot_paid = sum([s["total_paid"] for s in self.sources_data]) if self.sources_data else sum([d["total_paid"] for d in self.doctors_data])
        tot_bal = sum([s["total_balance"] for s in self.sources_data]) if self.sources_data else sum([d["total_balance"] for d in self.doctors_data])

        self.kpi_revenue.set_value(f"{tot_rev:,.2f} ج.م")
        self.kpi_visits.set_value(f"{tot_vis} زيارة")
        self.kpi_paid.set_value(f"{tot_paid:,.2f} ج.م")
        self.kpi_balance.set_value(f"{tot_bal:,.2f} ج.م")

        # 6. Update Visual Charts Data
        doc_chart_items = [
            {"label": d["doctor_name"] or "غير محدد", "value": d["total_amount"], "display_val": f"{d['total_amount']:,.0f} ج.م", "color": "#0F766E"}
            for d in self.doctors_data[:6]
        ]
        self.chart_doctors.set_data(doc_chart_items)

        dep_chart_items = [
            {"label": dep["department_name"], "value": dep["total_revenue"], "display_val": f"{dep['total_revenue']:,.0f} ج.م", "color": "#0284C7"}
            for dep in self.departments_data[:6]
        ]
        self.chart_departments.set_data(dep_chart_items)

        src_chart_items = [
            {"label": s["source_name"], "value": s["total_amount"], "display_val": f"{s['total_amount']:,.0f} ج.م", "color": "#D97706"}
            for s in self.sources_data[:6]
        ]
        self.chart_sources.set_data(src_chart_items)

        staff_chart_items = [
            {"label": st["full_name"], "value": st["visits_created"], "display_val": f"{st['visits_created']} زيارة", "color": "#7C3AED"}
            for st in self.staff_data[:6]
        ]
        self.chart_staff.set_data(staff_chart_items)



    def on_doctor_selected(self):
        selected_rows = self.doctors_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.doctors_data):
            return
        doc = self.doctors_data[row]
        self.selected_doctor_id = doc["doctor_id"]
        self.selected_doctor_name = doc["doctor_name"]
        self.load_doctor_patients(self.selected_doctor_id, self.selected_doctor_name)

    def load_doctor_patients(self, doctor_id, doctor_name):
        start_date, end_date = self._get_dates()
        patients_data = reports_service.get_doctor_patients_drilldown(doctor_id, start_date=start_date, end_date=end_date)
        self.lbl_doctor_drilldown_title.setText(f"<b>📋 تفاصيل المرضى المحولين من الطبيب:</b> {doctor_name} ({len(patients_data)} مريض/زيارة)")

        self.patients_table.setRowCount(len(patients_data))
        for row_idx, p in enumerate(patients_data):
            visit_date_str = (p.get("visit_date") or "")[:10]
            self.patients_table.setItem(row_idx, 0, QTableWidgetItem(str(p["invoice_number"])))
            self.patients_table.setItem(row_idx, 1, QTableWidgetItem(p["patient_name"]))
            self.patients_table.setItem(row_idx, 2, QTableWidgetItem(p["patient_phone"] or "-"))
            self.patients_table.setItem(row_idx, 3, QTableWidgetItem(visit_date_str))
            self.patients_table.setItem(row_idx, 4, QTableWidgetItem(p.get("tests_str", "-")))
            self.patients_table.setItem(row_idx, 5, QTableWidgetItem(f"{p['total_amount']:.2f}"))
            self.patients_table.setItem(row_idx, 6, QTableWidgetItem(f"{p['paid_amount']:.2f}"))
            self.patients_table.setItem(row_idx, 7, QTableWidgetItem(f"{p['balance']:.2f}"))

    def on_staff_selected(self):
        selected_rows = self.staff_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < 0 or row >= len(self.staff_data):
            return
        st = self.staff_data[row]
        self.selected_staff_id = st["user_id"]
        self.selected_staff_name = st["full_name"]
        self.load_staff_patients(self.selected_staff_id, self.selected_staff_name)

    def load_staff_patients(self, user_id, staff_name):
        start_date, end_date = self._get_dates()
        staff_patients_data = reports_service.get_staff_activity_drilldown(user_id, start_date=start_date, end_date=end_date)
        self.lbl_staff_drilldown_title.setText(f"<b>📋 سجل مرضا وعمليات الموظف:</b> {staff_name} ({len(staff_patients_data)} مريض/زيارة)")

        self.staff_patients_table.setRowCount(len(staff_patients_data))
        for row_idx, p in enumerate(staff_patients_data):
            visit_date_str = (p.get("visit_date") or "")[:10]
            self.staff_patients_table.setItem(row_idx, 0, QTableWidgetItem(str(p.get("invoice_number") or "-")))
            self.staff_patients_table.setItem(row_idx, 1, QTableWidgetItem(p["patient_name"]))
            self.staff_patients_table.setItem(row_idx, 2, QTableWidgetItem(p["patient_phone"] or "-"))
            self.staff_patients_table.setItem(row_idx, 3, QTableWidgetItem(visit_date_str))
            self.staff_patients_table.setItem(row_idx, 4, QTableWidgetItem(p.get("tests_str", "-")))
            self.staff_patients_table.setItem(row_idx, 5, QTableWidgetItem(f"{p['total_amount']:.2f}" if p.get('total_amount') is not None else "-"))
            self.staff_patients_table.setItem(row_idx, 6, QTableWidgetItem(f"{p['paid_amount']:.2f}" if p.get('paid_amount') is not None else "-"))
            self.staff_patients_table.setItem(row_idx, 7, QTableWidgetItem(f"{p['balance']:.2f}" if p.get('balance') is not None else "-"))

    # ==================== Export functionality ====================
    def export_current_tab_csv(self):
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index == 0:
            if self.selected_doctor_id is not None:
                title = f"مرضى الطبيب {self.selected_doctor_name}"
                target_table = self.patients_table
                default_filename = f"patients_doctor_{self.selected_doctor_id}.csv"
            else:
                title = "تقرير الأطباء المحولين"
                target_table = self.doctors_table
                default_filename = "referring_doctors_report.csv"
        elif current_tab_index == 1:
            title = "تقرير جهات الإحالة"
            target_table = self.sources_table
            default_filename = "referral_sources_report.csv"
        elif current_tab_index == 2:
            title = "تقرير إحصائيات الأقسام الطبية"
            target_table = self.departments_table
            default_filename = "departments_revenue_report.csv"
        else:
            if self.selected_staff_id is not None:
                title = f"عمليات الموظف {self.selected_staff_name}"
                target_table = self.staff_patients_table
                default_filename = f"staff_activity_user_{self.selected_staff_id}.csv"
            else:
                title = "تقرير إنتاجية موظفي المعمل"
                target_table = self.staff_table
                default_filename = "staff_productivity_report.csv"

        from app.config import get_exports_patients_dir
        import os as _os
        path, _ = QFileDialog.getSaveFileName(
            self, f"تصدير {title}",
            _os.path.join(get_exports_patients_dir(), default_filename),
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = []
                for col in range(target_table.columnCount()):
                    headers.append(target_table.horizontalHeaderItem(col).text())
                writer.writerow(headers)

                for row in range(target_table.rowCount()):
                    row_data = []
                    for col in range(target_table.columnCount()):
                        item = target_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            QMessageBox.information(
                self, "✅ تم التصدير بنجاح",
                f"تم تصدير التقرير بنجاح!\n\n"
                f"📁 مسار الحفظ:\n{path}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ الملف: {exc}")

