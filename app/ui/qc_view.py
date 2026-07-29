from PySide2.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QHeaderView, QLabel,
                                QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.services import catalog_service, qc_service
from app.ui.animated_button import AnimatedButton
from app.ui.qc_chart_widget import LeveyJenningsChartWidget
from app.ui.widgets import HintBanner

STATUS_LABELS = {"InControl": "ضمن النطاق", "Warning": "تحذير", "OutOfControl": "خارج السيطرة"}


class QCView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        self.tests = []
        self.parameters = []

        outer = QVBoxLayout(self)
        title = QLabel("مراقبة الجودة الداخلية (QC)")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "سجّل قيمة عينة الكنترول اليومية لكل معيار، وتابع رسم Levey-Jennings البياني للتأكد من "
            "استقرار الجهاز - أول مرة تحتاج تحديد المتوسط والانحراف المعياري المستهدفين."
        ))

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)

        selectors_row = QHBoxLayout()
        selectors_row.addWidget(QLabel("التحليل:"))
        self.test_combo = QComboBox()
        self.test_combo.currentIndexChanged.connect(self.on_test_changed)
        selectors_row.addWidget(self.test_combo, 1)

        selectors_row.addWidget(QLabel("المعيار:"))
        self.parameter_combo = QComboBox()
        self.parameter_combo.currentIndexChanged.connect(self.refresh_chart)
        selectors_row.addWidget(self.parameter_combo, 1)

        selectors_row.addWidget(QLabel("مستوى الكنترول:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(qc_service.CONTROL_LEVELS)
        self.level_combo.currentIndexChanged.connect(self.refresh_chart)
        selectors_row.addWidget(self.level_combo)
        card_layout.addLayout(selectors_row)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("المتوسط المستهدف (Mean):"))
        self.mean_spin = QDoubleSpinBox()
        self.mean_spin.setRange(-1000000, 1000000)
        self.mean_spin.setDecimals(3)
        target_row.addWidget(self.mean_spin)

        target_row.addWidget(QLabel("الانحراف المعياري (SD):"))
        self.sd_spin = QDoubleSpinBox()
        self.sd_spin.setRange(0, 1000000)
        self.sd_spin.setDecimals(3)
        target_row.addWidget(self.sd_spin)

        save_target_button = QPushButton("حفظ الهدف")
        save_target_button.clicked.connect(self.save_target)
        target_row.addWidget(save_target_button)
        card_layout.addLayout(target_row)

        entry_row = QHBoxLayout()
        entry_row.addWidget(QLabel("قيمة القياس اليوم:"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1000000, 1000000)
        self.value_spin.setDecimals(3)
        entry_row.addWidget(self.value_spin)

        record_button = AnimatedButton("تسجيل القيمة")
        record_button.setObjectName("Primary")
        record_button.clicked.connect(self.record_value)
        entry_row.addWidget(record_button)
        card_layout.addLayout(entry_row)

        self.chart = LeveyJenningsChartWidget()
        card_layout.addWidget(self.chart)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["التاريخ والوقت", "القيمة", "الحالة"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setMaximumHeight(160)
        card_layout.addWidget(self.history_table)

        outer.addWidget(card)

        self.refresh()

    def _current_user_id(self):
        return getattr(self.current_user, "user_id", None) if self.current_user else None

    def refresh(self):
        self.tests = catalog_service.search_tests()
        self.test_combo.blockSignals(True)
        self.test_combo.clear()
        for t in self.tests:
            self.test_combo.addItem(t["name"], t["id"])
        self.test_combo.blockSignals(False)
        self.on_test_changed()

    def on_test_changed(self, *_args):
        test_id = self.test_combo.currentData()
        self.parameter_combo.blockSignals(True)
        self.parameter_combo.clear()
        if test_id is not None:
            details = catalog_service.get_test_with_details(test_id)
            self.parameters = details.get("parameters", []) if details else []
            for p in self.parameters:
                self.parameter_combo.addItem(p["name"], p["id"])
        self.parameter_combo.blockSignals(False)
        self.refresh_chart()

    def _selected_parameter_id(self):
        return self.parameter_combo.currentData()

    def refresh_chart(self, *_args):
        parameter_id = self._selected_parameter_id()
        level = self.level_combo.currentText()
        if parameter_id is None:
            self.chart.set_data([], 0, 0)
            self.history_table.setRowCount(0)
            return

        target = qc_service.get_qc_target(parameter_id, level)
        if target:
            self.mean_spin.setValue(target["target_mean"])
            self.sd_spin.setValue(target["target_sd"])
        else:
            self.mean_spin.setValue(0)
            self.sd_spin.setValue(0)

        history = qc_service.get_qc_history(parameter_id, level)
        mean = target["target_mean"] if target else 0
        sd = target["target_sd"] if target else 0
        self.chart.set_data(history, mean, sd)

        self.history_table.setRowCount(len(history))
        for row_idx, r in enumerate(reversed(history)):
            self.history_table.setItem(row_idx, 0, QTableWidgetItem(r["recorded_at"].replace("T", " ")))
            self.history_table.setItem(row_idx, 1, QTableWidgetItem(str(r["measured_value"])))
            self.history_table.setItem(row_idx, 2, QTableWidgetItem(STATUS_LABELS.get(r["status"], r["status"])))

    def save_target(self):
        parameter_id = self._selected_parameter_id()
        if parameter_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر تحليلًا ومعيارًا أولًا")
            return
        qc_service.save_qc_target(parameter_id, self.level_combo.currentText(),
                                  self.mean_spin.value(), self.sd_spin.value())
        QMessageBox.information(self, "تم الحفظ", "تم حفظ الهدف بنجاح")
        self.refresh_chart()

    def record_value(self):
        parameter_id = self._selected_parameter_id()
        if parameter_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر تحليلًا ومعيارًا أولًا")
            return
        ok, message = qc_service.record_qc_value(
            parameter_id, self.level_combo.currentText(), self.value_spin.value(), user_id=self._current_user_id()
        )
        if ok:
            QMessageBox.information(self, "تم التسجيل", message)
        else:
            QMessageBox.warning(self, "تنبيه", message)
        self.refresh_chart()
