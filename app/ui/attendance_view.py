from PySide2.QtCore import QDate
from PySide2.QtWidgets import (QComboBox, QDateEdit, QFrame, QHBoxLayout, QHeaderView, QLabel,
                                QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.services import attendance_service, user_service
from app.ui.animated_button import AnimatedButton
from app.ui.styles import get_color
from app.ui.widgets import HintBanner


class AttendanceView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user

        outer = QVBoxLayout(self)
        title = QLabel("الحضور والانصراف")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "سجّل حضورك وانصرافك من هنا في بداية ونهاية كل يوم عمل، وراجع تقرير الحضور لكل الموظفين بالأسفل."
        ))

        my_card = QFrame()
        my_card.setObjectName("Card")
        my_layout = QVBoxLayout(my_card)
        my_layout.addWidget(QLabel("<b>تسجيل حضورك اليوم:</b>"))

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 13px; color: {get_color('primary_text')};")
        my_layout.addWidget(self.status_label)

        buttons_row = QHBoxLayout()
        self.check_in_button = AnimatedButton("✅ تسجيل حضور")
        self.check_in_button.setObjectName("Primary")
        self.check_in_button.clicked.connect(self.do_check_in)
        buttons_row.addWidget(self.check_in_button)

        self.check_out_button = AnimatedButton("🚪 تسجيل انصراف")
        self.check_out_button.setObjectName("Danger")
        self.check_out_button.clicked.connect(self.do_check_out)
        buttons_row.addWidget(self.check_out_button)
        my_layout.addLayout(buttons_row)

        outer.addWidget(my_card)

        report_card = QFrame()
        report_card.setObjectName("Card")
        report_layout = QVBoxLayout(report_card)
        report_layout.addWidget(QLabel("<b>تقرير الحضور والانصراف لكل الموظفين:</b>"))

        filters_row = QHBoxLayout()
        filters_row.addWidget(QLabel("من:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        filters_row.addWidget(self.date_from)

        filters_row.addWidget(QLabel("إلى:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filters_row.addWidget(self.date_to)

        filters_row.addWidget(QLabel("الموظف:"))
        self.staff_combo = QComboBox()
        filters_row.addWidget(self.staff_combo)

        refresh_button = QPushButton("تحديث")
        refresh_button.clicked.connect(self.refresh_report)
        filters_row.addWidget(refresh_button)
        filters_row.addStretch()
        report_layout.addLayout(filters_row)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(4)
        self.report_table.setHorizontalHeaderLabels(["الموظف", "وقت الحضور", "وقت الانصراف", "عدد الساعات"])
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        report_layout.addWidget(self.report_table)

        outer.addWidget(report_card)

        self.refresh()

    def _current_user_id(self):
        return getattr(self.current_user, "user_id", None) if self.current_user else None

    def refresh(self):
        self._refresh_status()
        self._refresh_staff_combo()
        self.refresh_report()

    def _refresh_status(self):
        uid = self._current_user_id()
        open_session = attendance_service.get_open_session(uid) if uid else None
        if open_session:
            self.status_label.setText(f"✅ أنت مسجَّل حضور منذ الساعة {open_session['check_in'][11:16]}")
            self.check_in_button.setEnabled(False)
            self.check_out_button.setEnabled(True)
        else:
            self.status_label.setText("⚪ لم تسجّل حضورك بعد اليوم")
            self.check_in_button.setEnabled(True)
            self.check_out_button.setEnabled(False)

    def _refresh_staff_combo(self):
        current_selection = self.staff_combo.currentData()
        self.staff_combo.clear()
        self.staff_combo.addItem("الكل", None)
        for user in user_service.get_users():
            if user["is_active"]:
                self.staff_combo.addItem(user["full_name"], user["id"])
        index = self.staff_combo.findData(current_selection)
        if index >= 0:
            self.staff_combo.setCurrentIndex(index)

    def do_check_in(self):
        uid = self._current_user_id()
        ok, message = attendance_service.check_in(uid)
        if not ok:
            QMessageBox.warning(self, "تنبيه", message)
        self.refresh()

    def do_check_out(self):
        uid = self._current_user_id()
        ok, message = attendance_service.check_out(uid)
        if not ok:
            QMessageBox.warning(self, "تنبيه", message)
        self.refresh()

    def refresh_report(self):
        start_date = self.date_from.date().toString("yyyy-MM-dd")
        end_date = self.date_to.date().toString("yyyy-MM-dd")
        user_id = self.staff_combo.currentData()
        records = attendance_service.get_attendance_report(start_date=start_date, end_date=end_date, user_id=user_id)

        self.report_table.setRowCount(len(records))
        for row_idx, r in enumerate(records):
            self.report_table.setItem(row_idx, 0, QTableWidgetItem(r["full_name"]))
            self.report_table.setItem(row_idx, 1, QTableWidgetItem(r["check_in"].replace("T", " ")))
            self.report_table.setItem(row_idx, 2, QTableWidgetItem(r["check_out"].replace("T", " ") if r["check_out"] else "لا يزال حاضرًا"))
            self.report_table.setItem(row_idx, 3, QTableWidgetItem(f"{r['hours_worked']:.2f}" if r["hours_worked"] is not None else "-"))
