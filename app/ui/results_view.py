import subprocess
import sys

from PySide2.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                                QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from app.reports.lab_report import generate_lab_report_pdf
from app.services import catalog_service, result_service
from app.services.result_service import FLAG_LABELS
from app.ui.widgets import HintBanner


class ResultsView(QWidget):
    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()
        outer = QVBoxLayout(self)
        title = QLabel("نتائج التحاليل")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "الفني يدخل النتائج من تبويب «إدخال النتائج»، ثم يراجعها ويعتمدها مسؤول آخر من تبويب "
            "«المراجعة والاعتماد» - ولا تُطبع أي نتيجة PDF إلا بعد الاعتماد."
        ))

        tabs = QTabWidget()
        outer.addWidget(tabs)
        tabs.addTab(self._build_entry_tab(), "إدخال النتائج")
        tabs.addTab(self._build_review_tab(), "المراجعة والاعتماد")

    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold; color: #0B4F6C;")
        return label

    def _get_range_text(self, p):
        if p.get("range_low") is not None and p.get("range_high") is not None:
            return f"{p['range_low']} - {p['range_high']}"
        if p.get("range_text"):
            return p["range_text"]
        return "غير محدد"

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

    def refresh(self):
        self.refresh_entry()
        self.refresh_review()

    # ==================== Entry tab: technician writes the result ====================
    def _build_entry_tab(self):
        widget = QWidget()
        self.pending_orders = []
        self.current_order = None
        self.parameter_inputs = []  # list of (parameter_id, data_type, line_edit, range)
        self._limit = 50
        self._offset = 0

        outer = QVBoxLayout(widget)
        columns = QHBoxLayout()
        outer.addLayout(columns)

        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.addWidget(self._label_bold("التحاليل قيد الإدخال"))
        self.pending_list = QListWidget()
        self.pending_list.setToolTip("اختر تحليلًا لبدء إدخال نتيجته")
        self.pending_list.itemClicked.connect(self.on_select_order)
        list_layout.addWidget(self.pending_list)
        load_more = QPushButton("تحميل المزيد")
        load_more.clicked.connect(self.load_more)
        list_layout.addWidget(load_more)
        columns.addWidget(list_card, 1)

        self.entry_card = QFrame()
        self.entry_card.setObjectName("Card")
        self.entry_layout = QVBoxLayout(self.entry_card)
        self.entry_title = self._label_bold("اختر تحليلًا من القائمة")
        self.entry_layout.addWidget(self.entry_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.params_container = QWidget()
        self.params_layout = QVBoxLayout(self.params_container)
        self.scroll_area.setWidget(self.params_container)
        self.entry_layout.addWidget(self.scroll_area)

        buttons_row = QHBoxLayout()
        self.draft_button = QPushButton("حفظ كمسودة")
        self.draft_button.setToolTip("يحفظ ما تم إدخاله حتى الآن دون إرساله للمراجعة - يمكن إكماله لاحقًا")
        self.draft_button.clicked.connect(lambda: self.save_results(False))
        self.complete_button = QPushButton("حفظ وإرسال للمراجعة")
        self.complete_button.setObjectName("Primary")
        self.complete_button.setToolTip("يرسل النتيجة كاملة لتبويب المراجعة والاعتماد")
        self.complete_button.clicked.connect(lambda: self.save_results(True))
        buttons_row.addWidget(self.complete_button)
        buttons_row.addWidget(self.draft_button)
        self.entry_layout.addLayout(buttons_row)

        self.entry_message = QLabel("")
        self.entry_message.setWordWrap(True)
        self.entry_layout.addWidget(self.entry_message)

        columns.addWidget(self.entry_card, 2)
        self.results_list = self.pending_list  # legacy alias used by earlier tests

        self.refresh_entry()
        return widget

    def refresh_entry(self):
        self._offset = 0
        self.pending_orders = result_service.get_pending_orders(limit=self._limit, offset=self._offset)
        self.pending_list.clear()
        for o in self.pending_orders:
            item = QListWidgetItem(f"{o['test_name']}\n{o['patient_name']}")
            self.pending_list.addItem(item)

    def load_more(self):
        self._offset += self._limit
        more = result_service.get_pending_orders(limit=self._limit, offset=self._offset)
        if not more:
            return
        self.pending_orders.extend(more)
        for o in more:
            item = QListWidgetItem(f"{o['test_name']}\n{o['patient_name']}")
            self.pending_list.addItem(item)

    def on_select_order(self, item):
        row = self.pending_list.row(item)
        order_id = self.pending_orders[row]["id"]
        self.load_order(order_id)

    def load_order(self, order_id):
        view = result_service.get_order_entry_view(order_id)
        self.current_order = view

        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.parameter_inputs = []

        self.entry_title.setText(f"{view['test_name']} - {view['patient_name']}")

        for p in view["parameters"]:
            row = QHBoxLayout()
            range_text = self._get_range_text(p)
            unit_text = p.get("unit") or "-"
            name_label = QLabel(f"{p['name']} | الوحدة: {unit_text}")
            name_label.setMinimumWidth(220)
            range_label = QLabel(f"المدى الطبيعي: {range_text}")
            range_label.setStyleSheet("color: #6B7280;")
            range_label.setMinimumWidth(180)
            value_edit = QLineEdit()
            if p["data_type"] == "Numeric" and p.get("existing_numeric") is not None:
                value_edit.setText(str(p["existing_numeric"]))
            elif p.get("existing_text"):
                value_edit.setText(p["existing_text"])

            row.addWidget(name_label)
            row.addWidget(range_label)
            row.addWidget(value_edit)
            self.params_layout.addLayout(row)
            self.parameter_inputs.append((p["parameter_id"], p["data_type"], value_edit, p))

        self.params_layout.addStretch()

    def save_results(self, mark_completed: bool):
        if self.current_order is None:
            return
        values = []
        for parameter_id, data_type, edit, p in self.parameter_inputs:
            text = edit.text().strip()
            numeric_value = None
            text_value = None
            if data_type == "Numeric":
                if text:
                    try:
                        numeric_value = float(text)
                    except ValueError:
                        text_value = text
            else:
                text_value = text or None
            values.append({
                "parameter_id": parameter_id, "numeric_value": numeric_value, "text_value": text_value,
                "low": p["range_low"], "high": p["range_high"], "normal_text": p.get("range_text"),
                "data_type": data_type,
            })
        result_service.save_results(self.current_order["id"], values, mark_completed)
        if mark_completed:
            self.entry_message.setText("تم الحفظ وإرساله لقائمة المراجعة والاعتماد.")
            self.entry_message.setStyleSheet("color: #146C8E;")
        else:
            self.entry_message.setText("تم حفظ المسودة.")
            self.entry_message.setStyleSheet("color: #6B7280;")
        self.current_order = None
        self.entry_title.setText("اختر تحليلًا من القائمة")
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.refresh_entry()
        self.refresh_review()

    # ==================== Review tab: a reviewer approves, then the PDF is printed ====================
    def _build_review_tab(self):
        widget = QWidget()
        self.review_orders = []
        self.current_review_order_id = None
        self._review_limit = 50
        self._review_offset = 0

        outer = QVBoxLayout(widget)
        columns = QHBoxLayout()
        outer.addLayout(columns)

        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.addWidget(self._label_bold("بانتظار المراجعة"))
        self.review_list = QListWidget()
        self.review_list.itemClicked.connect(self.on_select_review_order)
        list_layout.addWidget(self.review_list)
        review_load_more = QPushButton("تحميل المزيد")
        review_load_more.clicked.connect(self.load_more_review)
        list_layout.addWidget(review_load_more)
        columns.addWidget(list_card, 1)

        detail_card = QFrame()
        detail_card.setObjectName("Card")
        self.review_detail_layout = QVBoxLayout(detail_card)
        self.review_title = self._label_bold("اختر تحليلًا لمراجعته")
        self.review_detail_layout.addWidget(self.review_title)

        self.review_scroll = QScrollArea()
        self.review_scroll.setWidgetResizable(True)
        self.review_values_container = QWidget()
        self.review_values_layout = QVBoxLayout(self.review_values_container)
        self.review_scroll.setWidget(self.review_values_container)
        self.review_detail_layout.addWidget(self.review_scroll)

        review_buttons = QHBoxLayout()
        self.approve_button = QPushButton("اعتماد وطباعة PDF")
        self.approve_button.setObjectName("Primary")
        self.approve_button.setToolTip("يعتمد النتيجة نهائيًا وينشئ تقرير PDF جاهزًا للطباعة فورًا")
        self.approve_button.clicked.connect(self.approve_current_order)
        self.reject_button = QPushButton("إرجاع للتعديل")
        self.reject_button.setToolTip("لو وُجد خطأ في القيم، يعيد التحليل لتبويب الإدخال لتصحيحه")
        self.reject_button.clicked.connect(self.reject_current_order)
        review_buttons.addWidget(self.approve_button)
        review_buttons.addWidget(self.reject_button)
        self.review_detail_layout.addLayout(review_buttons)

        self.review_message = QLabel("")
        self.review_message.setWordWrap(True)
        self.review_detail_layout.addWidget(self.review_message)

        columns.addWidget(detail_card, 2)

        self.refresh_review()
        return widget

    def refresh_review(self):
        self._review_offset = 0
        self.review_orders = result_service.get_orders_pending_review(limit=self._review_limit, offset=self._review_offset)
        self.review_list.clear()
        for o in self.review_orders:
            self.review_list.addItem(QListWidgetItem(f"{o['test_name']}\n{o['patient_name']}"))
        self.current_review_order_id = None
        self.review_title.setText("اختر تحليلًا لمراجعته")
        self._clear_review_values()

    def load_more_review(self):
        self._review_offset += self._review_limit
        more = result_service.get_orders_pending_review(limit=self._review_limit, offset=self._review_offset)
        if not more:
            return
        self.review_orders.extend(more)
        for o in more:
            self.review_list.addItem(QListWidgetItem(f"{o['test_name']}\n{o['patient_name']}"))

    def _clear_review_values(self):
        while self.review_values_layout.count():
            child = self.review_values_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_select_review_order(self, item):
        row = self.review_list.row(item)
        order_id = self.review_orders[row]["id"]
        self.current_review_order_id = order_id
        data = result_service.get_report_data(order_id)
        self._clear_review_values()
        if data is None:
            return
        self.review_title.setText(f"{data['test_name']} - {data['patient_name']}")
        for p in data["parameters"]:
            value = p["numeric_value"] if p["numeric_value"] is not None else (p.get("text_value") or "-")
            range_text = self._get_range_text(p)
            unit_text = p.get("unit") or "-"
            flag = p.get("flag", "Normal")
            color = "#C62828" if flag in ("High", "Low", "Abnormal") else "#1A1A1A"
            flag_display = FLAG_LABELS.get(flag, flag)
            line = QLabel(
                f"{p['name']} | القيمة: {value} | الوحدة: {unit_text} | المدى الطبيعي: {range_text} | [{flag_display}]"
            )
            line.setStyleSheet(f"color: {color};")
            self.review_values_layout.addWidget(line)
        self.review_values_layout.addStretch()
        self.review_message.setText("")

    def _current_user_id(self):
        return getattr(self.current_user, "user_id", None) if self.current_user else None

    def approve_current_order(self):
        if self.current_review_order_id is None:
            return
        order_id = self.current_review_order_id
        result_service.approve_order(order_id, user_id=self._current_user_id())
        self.review_message.setText("جاري إعداد وتحضير تقرير النتيجة PDF...")
        self.approve_button.setEnabled(False)

        def _generate_pdf():
            data = result_service.get_report_data(order_id)
            settings = catalog_service.get_lab_settings()
            return generate_lab_report_pdf(
                data["patient_name"], data["gender"], data["age_years"], data["test_name"],
                data["parameters"], settings, data["invoice_number"],
            )

        def _on_done(path):
            self.approve_button.setEnabled(True)
            self.review_message.setText("تم اعتماد النتيجة، وتم فتح تقرير PDF جاهز للطباعة.")
            self.review_message.setStyleSheet("color: #146C8E;")
            self._open_file(path)
            self.refresh_review()

        def _on_err(err):
            self.approve_button.setEnabled(True)
            self.review_message.setText(f"حدث خطأ أثناء إنتاج التقرير: {err}")
            self.review_message.setStyleSheet("color: #C62828;")

        from app.utils.worker import run_in_background
        run_in_background(_generate_pdf, on_success=_on_done, on_error=_on_err)

    def reject_current_order(self):
        if self.current_review_order_id is None:
            return
        result_service.send_back_for_edit(self.current_review_order_id, user_id=self._current_user_id())
        self.review_message.setText("تم إرجاع التحليل لقائمة الإدخال للتعديل.")
        self.review_message.setStyleSheet("color: #6B7280;")
        self.refresh_review()
        self.refresh_entry()
