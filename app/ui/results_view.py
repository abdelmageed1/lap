import sys
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                                QMessageBox, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget)


from app.reports.lab_report import generate_lab_report_pdf
from app.services import auth_service, auto_calc, catalog_service, result_service
from app.services.result_service import FLAG_LABELS
from app.ui.animated_button import AnimatedButton
from app.ui.styles import get_color
from app.ui.widgets import HintBanner


class ResultsView(QWidget):
    def __init__(self, current_user=None):
        self.current_user = current_user
        self.last_pdf_path = None
        super().__init__()

        outer = QVBoxLayout(self)
        title = QLabel("نتائج التحاليل")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "الفني يدخل النتائج من تبويب «إدخال النتائج»، ثم يراجعها ويعتمدها مسؤول آخر من تبويب "
            "«المراجعة والاعتماد» - ولا تُطبع أي نتيجة PDF إلا بعد الاعتماد. "
            "يُمكن للأدمن إعادة فتح النتائج المعتمدة من التبويب المخصص."
        ))

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)
        self.tabs.addTab(self._build_entry_tab(), "إدخال النتائج ✍️")
        self.tabs.addTab(self._build_review_tab(), "المراجعة والاعتماد 📜")

        if self._is_admin():
            self.tabs.addTab(self._build_reopen_tab(), "النتائج المعتمدة (إعادة فتح 🔓)")

    def _is_admin(self) -> bool:
        if not self.current_user:
            return True
        if hasattr(self.current_user, "can_delete") and self.current_user.can_delete("Results"):
            return True
        if hasattr(self.current_user, "role_name") and self.current_user.role_name in ("مدير النظام", "Admin"):
            return True
        return False


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
        if hasattr(self, "refresh_reopen"):
            self.refresh_reopen()


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

        self.entry_search_edit = QLineEdit()
        self.entry_search_edit.setPlaceholderText("🔍 ابحث باسم المريض، رقم الفاتورة، أو التحليل...")
        self.entry_search_edit.setStyleSheet("padding: 6px 10px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.entry_search_edit.textChanged.connect(lambda *args: self.refresh_entry())
        list_layout.addWidget(self.entry_search_edit)

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
        query = self.entry_search_edit.text().strip() if hasattr(self, "entry_search_edit") else ""
        self.pending_orders = result_service.get_pending_orders(query=query, limit=self._limit, offset=self._offset)
        self.pending_list.clear()
        if not self.pending_orders:
            empty_item = QListWidgetItem("✨ لا توجد تحاليل بانتظار إدخال النتائج حالياً")
            empty_item.setFlags(Qt.NoItemFlags)
            empty_item.setTextAlignment(Qt.AlignCenter)
            self.pending_list.addItem(empty_item)
        else:
            for o in self.pending_orders:
                inv_str = f"فاتورة #{o.get('invoice_number', '-')}: " if o.get('invoice_number') else ""
                item = QListWidgetItem(f"{inv_str}{o['test_name']}\n👤 {o['patient_name']}")
                self.pending_list.addItem(item)

    def load_more(self):
        self._offset += self._limit
        query = self.entry_search_edit.text().strip() if hasattr(self, "entry_search_edit") else ""
        more = result_service.get_pending_orders(query=query, limit=self._limit, offset=self._offset)
        if not more:
            return
        self.pending_orders.extend(more)
        for o in more:
            inv_str = f"فاتورة #{o.get('invoice_number', '-')}: " if o.get('invoice_number') else ""
            item = QListWidgetItem(f"{inv_str}{o['test_name']}\n👤 {o['patient_name']}")
            self.pending_list.addItem(item)


    def on_select_order(self, item):
        if not self.pending_orders or item.flags() == Qt.NoItemFlags:
            return
        row = self.pending_list.row(item)
        if row < 0 or row >= len(self.pending_orders):
            return
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
            param_card = QFrame()
            param_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {get_color('bg_subtle')};
                    border: 1px solid {get_color('border')};
                    border-radius: 8px;
                }}
            """)
            card_layout = QVBoxLayout(param_card)
            card_layout.setSpacing(8)
            card_layout.setContentsMargins(14, 12, 14, 12)

            top_row = QHBoxLayout()
            unit_text = p.get("unit") or "-"
            name_label = QLabel(f"<b>{p['name']}</b> <span style='color: {get_color('text_muted')};'>(الوحدة: {unit_text})</span>")
            name_label.setStyleSheet(f"font-size: 14px; color: {get_color('text_emphasis')};")

            range_text = self._get_range_text(p)
            range_label = QLabel(f"المدى الطبيعي: <b>{range_text}</b>")
            range_label.setStyleSheet(f"color: {get_color('accent')}; background: {get_color('accent_bg')}; padding: 4px 10px; border-radius: 6px; font-size: 12px;")

            top_row.addWidget(name_label)
            top_row.addStretch()
            top_row.addWidget(range_label)

            value_edit = QLineEdit()
            value_edit.setPlaceholderText(f"أدخل النتيجة (المدى الطبيعي: {range_text})")
            value_edit.setStyleSheet("font-size: 14px; padding: 8px 12px; border: 1px solid #CBD5E1; border-radius: 6px; background: white;")

            if p.get("numeric_value") is not None:
                value_edit.setText(str(p["numeric_value"]))
            elif p.get("text_value"):
                value_edit.setText(p["text_value"])

            tooltip_text = self._get_range_text(p)
            if tooltip_text:
                value_edit.setToolTip(f"المدى الطبيعي: {tooltip_text}")

            value_edit.textChanged.connect(lambda txt, edit=value_edit, param=p: self._on_param_value_changed(txt, edit, param))

            card_layout.addLayout(top_row)
            card_layout.addWidget(value_edit)

            self.params_layout.addWidget(param_card)
            self.parameter_inputs.append((p["parameter_id"], p["data_type"], value_edit, p))

        self.params_layout.addStretch()

    def _on_param_value_changed(self, text: str, edit: QLineEdit, param: dict):
        stripped = text.strip()
        if stripped.lower() == "n":
            edit.blockSignals(True)
            edit.setText("Negative")
            edit.blockSignals(False)
        elif stripped.lower() == "p":
            edit.blockSignals(True)
            edit.setText("Positive")
            edit.blockSignals(False)

        if not self.current_order:
            return

        test_name = self.current_order.get("test_name", "")
        if not (auto_calc.is_cbc_test(test_name) or auto_calc.is_creatinine_clearance_test(test_name)):
            return

        input_values = {}
        param_edits = {}
        for parameter_id, data_type, line_edit, p_info in self.parameter_inputs:
            key = auto_calc.normalize_param_key(p_info["name"])
            val_str = line_edit.text().strip()
            input_values[key] = val_str
            param_edits[key] = line_edit

        if auto_calc.is_cbc_test(test_name):
            calc_results = auto_calc.calculate_cbc(input_values)
        else:
            calc_results = auto_calc.calculate_creatinine_clearance(input_values)

        for key, calc_val in calc_results.items():
            if key in param_edits:
                target_edit = param_edits[key]
                if calc_val is not None:
                    new_str = str(calc_val)
                    if target_edit.text() != new_str:
                        target_edit.blockSignals(True)
                        target_edit.setText(new_str)
                        target_edit.blockSignals(False)

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
            self.entry_message.setStyleSheet(f"color: {get_color('primary')};")
        else:
            self.entry_message.setText("تم حفظ المسودة.")
            self.entry_message.setStyleSheet(f"color: {get_color('text_muted')};")
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

        self.review_search_edit = QLineEdit()
        self.review_search_edit.setPlaceholderText("🔍 ابحث باسم المريض، رقم الفاتورة، أو التحليل...")
        self.review_search_edit.setStyleSheet("padding: 6px 10px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.review_search_edit.textChanged.connect(lambda *args: self.refresh_review())
        list_layout.addWidget(self.review_search_edit)

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

        self.open_location_button = AnimatedButton("فتح موقع الملف 📁")
        self.open_location_button.setToolTip("فتح مستكشف الملفات (File Explorer) لتحديد مجلد حفظ تقرير الـ PDF")
        self.open_location_button.setStyleSheet("""
            QPushButton {
                background-color: #0F766E;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0D9488;
            }
        """)
        self.open_location_button.clicked.connect(lambda: self.open_file_location())

        review_buttons.addWidget(self.approve_button)
        review_buttons.addWidget(self.open_location_button)
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
        query = self.review_search_edit.text().strip() if hasattr(self, "review_search_edit") else ""
        self.review_orders = result_service.get_orders_pending_review(query=query, limit=self._review_limit, offset=self._review_offset)
        self.review_list.clear()
        if not self.review_orders:
            empty_item = QListWidgetItem("✨ لا توجد نتائج بانتظار المراجعة والاعتماد حالياً")
            empty_item.setFlags(Qt.NoItemFlags)
            empty_item.setTextAlignment(Qt.AlignCenter)
            self.review_list.addItem(empty_item)
        else:
            for o in self.review_orders:
                inv_str = f"فاتورة #{o.get('invoice_number', '-')}: " if o.get('invoice_number') else ""
                self.review_list.addItem(QListWidgetItem(f"{inv_str}{o['test_name']}\n👤 {o['patient_name']}"))
        self.current_review_order_id = None
        self.review_title.setText("اختر تحليلًا لمراجعته")
        self._clear_review_values()

    def load_more_review(self):
        self._review_offset += self._review_limit
        query = self.review_search_edit.text().strip() if hasattr(self, "review_search_edit") else ""
        more = result_service.get_orders_pending_review(query=query, limit=self._review_limit, offset=self._review_offset)
        if not more:
            return
        self.review_orders.extend(more)
        for o in more:
            inv_str = f"فاتورة #{o.get('invoice_number', '-')}: " if o.get('invoice_number') else ""
            self.review_list.addItem(QListWidgetItem(f"{inv_str}{o['test_name']}\n👤 {o['patient_name']}"))


    def _clear_review_values(self):
        while self.review_values_layout.count():
            child = self.review_values_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_select_review_order(self, item):
        if not self.review_orders or item.flags() == Qt.NoItemFlags:
            return
        row = self.review_list.row(item)
        if row < 0 or row >= len(self.review_orders):
            return
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
            is_abnormal = flag in ("High", "Low", "Abnormal")
            
            flag_display = FLAG_LABELS.get(flag, flag)
            bg_color = "#FEF2F2" if is_abnormal else "#F8FAFC"
            border_color = "#FCA5A5" if is_abnormal else "#E2E8F0"
            text_color = "#991B1B" if is_abnormal else "#0F172A"
            flag_bg = "#FEE2E2" if is_abnormal else "#DCFCE7"
            flag_fg = "#991B1B" if is_abnormal else "#166534"

            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            layout = QHBoxLayout(card)
            layout.setContentsMargins(14, 10, 14, 10)

            name_lbl = QLabel(f"<b>{p['name']}</b> <span style='color: #64748B;'>(الوحدة: {unit_text})</span>")
            name_lbl.setStyleSheet(f"font-size: 14px; color: {text_color};")

            val_lbl = QLabel(f"القيمة: <b>{value}</b>")
            val_lbl.setStyleSheet(f"font-size: 14px; color: {text_color};")

            range_lbl = QLabel(f"المدى الطبيعي: {range_text}")
            range_lbl.setStyleSheet("font-size: 12px; color: #64748B;")

            flag_lbl = QLabel(flag_display)
            flag_lbl.setStyleSheet(f"background: {flag_bg}; color: {flag_fg}; font-weight: bold; padding: 4px 10px; border-radius: 6px; font-size: 12px;")

            layout.addWidget(name_lbl)
            layout.addStretch()
            layout.addWidget(val_lbl)
            layout.addSpacing(16)
            layout.addWidget(range_lbl)
            layout.addSpacing(16)
            layout.addWidget(flag_lbl)

            self.review_values_layout.addWidget(card)
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
            self.last_pdf_path = path
            self.review_message.setText(
                f"✅ تم اعتماد النتيجة بنجاح!\n"
                f"📁 تم حفظ الملف في المسار: {path}\n"
                f"🖨️ تم فتح تقرير PDF تلقائيًا للطباعة."
            )
            self.review_message.setStyleSheet(f"color: {get_color('primary')}; font-weight: bold;")
            self._open_file(path)
            self.refresh_review()

        def _on_err(err):
            self.approve_button.setEnabled(True)
            self.review_message.setText(f"حدث خطأ أثناء إنتاج التقرير: {err}")
            self.review_message.setStyleSheet(f"color: {get_color('danger')};")

        from app.utils.worker import run_in_background
        run_in_background(_generate_pdf, on_success=_on_done, on_error=_on_err)

    def _open_file(self, path):
        try:
            if sys.platform == "win32":
                import os
                os.startfile(path)  # noqa
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def open_file_location(self, target_path=None):
        import os
        import subprocess
        from app.config import REPORTS_DIR
        path = target_path or self.last_pdf_path or REPORTS_DIR
        try:
            if os.path.exists(path):
                if sys.platform == "win32":
                    if os.path.isfile(path):
                        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
                    else:
                        os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R" if os.path.isfile(path) else "", path])
                else:
                    subprocess.Popen(["xdg-open", os.path.dirname(path) if os.path.isfile(path) else path])
            else:
                os.makedirs(REPORTS_DIR, exist_ok=True)
                if sys.platform == "win32":
                    os.startfile(REPORTS_DIR)
        except Exception as exc:
            QMessageBox.warning(self, "خطأ فتح المجلد", f"تعذر فتح مسار الملف: {exc}")



    def reject_current_order(self):
        if self.current_review_order_id is None:
            return
        result_service.send_back_for_edit(self.current_review_order_id, user_id=self._current_user_id())
        self.review_message.setText("تم إرجاع التحليل لقائمة الإدخال للتعديل.")
        self.review_message.setStyleSheet(f"color: {get_color('text_muted')};")
        self.refresh_review()
        self.refresh_entry()

    # ==================== Re-open tab: Admin can re-open reviewed orders ====================
    def _build_reopen_tab(self):
        widget = QWidget()
        self.reopen_orders = []
        self.current_reopen_order_id = None
        self._reopen_limit = 50
        self._reopen_offset = 0

        outer = QVBoxLayout(widget)
        columns = QHBoxLayout()
        outer.addLayout(columns)

        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.addWidget(self._label_bold("النتائج المعتمدة مسبقًا"))

        self.reopen_search_edit = QLineEdit()
        self.reopen_search_edit.setPlaceholderText("🔍 ابحث باسم المريض، رقم الفاتورة، أو التحليل...")
        self.reopen_search_edit.setStyleSheet("padding: 6px 10px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.reopen_search_edit.textChanged.connect(lambda _: self.refresh_reopen())
        list_layout.addWidget(self.reopen_search_edit)

        self.reopen_list = QListWidget()
        self.reopen_list.itemClicked.connect(self.on_select_reopen_order)
        list_layout.addWidget(self.reopen_list)
        columns.addWidget(list_card, 1)

        detail_card = QFrame()
        detail_card.setObjectName("Card")
        self.reopen_detail_layout = QVBoxLayout(detail_card)
        self.reopen_title = self._label_bold("اختر نتيجة معتمدة لعرضها أو إعادتها للتعديل")
        self.reopen_detail_layout.addWidget(self.reopen_title)

        self.reopen_scroll = QScrollArea()
        self.reopen_scroll.setWidgetResizable(True)
        self.reopen_values_container = QWidget()
        self.reopen_values_layout = QVBoxLayout(self.reopen_values_container)
        self.reopen_scroll.setWidget(self.reopen_values_container)
        self.reopen_detail_layout.addWidget(self.reopen_scroll)

        reopen_btn_row = QHBoxLayout()
        self.print_reopen_pdf_btn = AnimatedButton("طباعة / فتح تقرير PDF 🖨️")
        self.print_reopen_pdf_btn.setObjectName("Primary")
        self.print_reopen_pdf_btn.setToolTip("توليد وفتح تقرير PDF المعتمد لهذا التحليل للطباعة فوراً")
        self.print_reopen_pdf_btn.clicked.connect(self.print_reopen_order_pdf)

        self.open_reopen_location_btn = AnimatedButton("فتح مجلد الحفظ 📁")
        self.open_reopen_location_btn.setToolTip("فتح مستكشف الملفات لمجلد تقارير الـ PDF")
        self.open_reopen_location_btn.setStyleSheet("""
            QPushButton {
                background-color: #0F766E;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0D9488;
            }
        """)
        self.open_reopen_location_btn.clicked.connect(lambda: self.open_file_location())

        self.reopen_button = AnimatedButton("إعادة الفتح للتعديل 🔓")
        self.reopen_button.setToolTip("يعيد هذه النتيجة المعتمدة إلى قائمة الإدخال للتعديل بطلب موافقة الأدمن")
        self.reopen_button.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #B45309;
            }
        """)
        self.reopen_button.clicked.connect(self.reopen_current_order)

        reopen_btn_row.addWidget(self.print_reopen_pdf_btn)
        reopen_btn_row.addWidget(self.open_reopen_location_btn)
        reopen_btn_row.addWidget(self.reopen_button)
        self.reopen_detail_layout.addLayout(reopen_btn_row)

        self.reopen_message = QLabel("")
        self.reopen_message.setWordWrap(True)
        self.reopen_detail_layout.addWidget(self.reopen_message)

        columns.addWidget(detail_card, 2)
        self.refresh_reopen()
        return widget

    def refresh_reopen(self):
        if not self._is_admin():
            return
        self._reopen_offset = 0
        query = self.reopen_search_edit.text().strip() if hasattr(self, "reopen_search_edit") else ""
        self.reopen_orders = result_service.get_reviewed_orders(query=query, limit=self._reopen_limit, offset=self._reopen_offset)
        self.reopen_list.clear()
        if not self.reopen_orders:
            empty_item = QListWidgetItem("✨ لا توجد نتائج معتمدة متاحة لفك الاعتماد حالياً")
            empty_item.setFlags(Qt.NoItemFlags)
            empty_item.setTextAlignment(Qt.AlignCenter)
            self.reopen_list.addItem(empty_item)
        else:
            for o in self.reopen_orders:
                inv_str = f"فاتورة #{o.get('invoice_number', '-')}: " if o.get('invoice_number') else ""
                self.reopen_list.addItem(QListWidgetItem(f"{inv_str}{o['test_name']}\n👤 {o['patient_name']} (معتمدة)"))
        self.current_reopen_order_id = None
        self.reopen_title.setText("اختر نتيجة معتمدة لعرضها أو إعادتها للتعديل")
        self._clear_reopen_values()


    def _clear_reopen_values(self):
        while self.reopen_values_layout.count():
            child = self.reopen_values_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def on_select_reopen_order(self, item):
        if not self.reopen_orders or item.flags() == Qt.NoItemFlags:
            return
        row = self.reopen_list.row(item)
        if row < 0 or row >= len(self.reopen_orders):
            return
        order_id = self.reopen_orders[row]["id"]
        self.current_reopen_order_id = order_id
        data = result_service.get_report_data(order_id)
        self._clear_reopen_values()
        if data is None:
            return
        self.reopen_title.setText(f"{data['test_name']} - {data['patient_name']} (معتمدة)")

        # Patient Header Summary Card
        patient_card = QFrame()
        patient_card.setStyleSheet(f"""
            QFrame {{
                background-color: {get_color('bg_subtle')};
                border: 1px solid {get_color('border')};
                border-radius: 8px;
            }}
        """)
        p_layout = QHBoxLayout(patient_card)
        p_layout.setContentsMargins(14, 10, 14, 10)

        p_info = QLabel(
            f"👤 <b>المريض:</b> {data['patient_name']} &nbsp;│&nbsp; "
            f"🧾 <b>فاتورة #:</b> {data.get('invoice_number', '-')} &nbsp;│&nbsp; "
            f"🚻 <b>الجنس/السن:</b> {data.get('gender', '-')} ({data.get('age_years', '-')} سنة)"
        )
        p_info.setStyleSheet(f"font-size: 13px; color: {get_color('primary_text')};")
        p_layout.addWidget(p_info)
        self.reopen_values_layout.addWidget(patient_card)

        # Parameter Cards
        for p in data["parameters"]:
            value = p["numeric_value"] if p["numeric_value"] is not None else (p.get("text_value") or "-")
            range_text = self._get_range_text(p)
            unit_text = p.get("unit") or "-"
            flag = p.get("flag", "Normal")
            is_abnormal = flag in ("High", "Low", "Abnormal", "H", "L", "Panic", "Critical")

            flag_display = FLAG_LABELS.get(flag, flag)
            bg_color = "#FEF2F2" if is_abnormal else "#F8FAFC"
            border_color = "#FCA5A5" if is_abnormal else "#E2E8F0"
            text_color = "#991B1B" if is_abnormal else "#0F172A"
            flag_bg = "#FEE2E2" if is_abnormal else "#DCFCE7"
            flag_fg = "#991B1B" if is_abnormal else "#166534"

            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            layout = QHBoxLayout(card)
            layout.setContentsMargins(14, 10, 14, 10)

            name_lbl = QLabel(f"<b>{p['name']}</b> <span style='color: #64748B;'>(الوحدة: {unit_text})</span>")
            name_lbl.setStyleSheet(f"font-size: 14px; color: {text_color};")

            val_lbl = QLabel(f"القيمة: <b>{value}</b>")
            val_lbl.setStyleSheet(f"font-size: 14px; color: {text_color};")

            range_lbl = QLabel(f"المدى الطبيعي: {range_text}")
            range_lbl.setStyleSheet("font-size: 12px; color: #64748B;")

            flag_lbl = QLabel(flag_display)
            flag_lbl.setStyleSheet(f"background: {flag_bg}; color: {flag_fg}; font-weight: bold; padding: 4px 10px; border-radius: 6px; font-size: 12px;")

            layout.addWidget(name_lbl)
            layout.addStretch()
            layout.addWidget(val_lbl)
            layout.addSpacing(16)
            layout.addWidget(range_lbl)
            layout.addSpacing(16)
            layout.addWidget(flag_lbl)

            self.reopen_values_layout.addWidget(card)
        self.reopen_values_layout.addStretch()
        self.reopen_message.setText("")

    def print_reopen_order_pdf(self):
        if self.current_reopen_order_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر نتيجة معتمدة أولاً لطباعة تقريرها")
            return
        order_id = self.current_reopen_order_id
        data = result_service.get_report_data(order_id)
        if not data:
            return
        settings = catalog_service.get_lab_settings()
        pdf_path = generate_lab_report_pdf(
            data["patient_name"], data["gender"], data["age_years"], data["test_name"],
            data["parameters"], settings, data["invoice_number"],
        )
        self.last_pdf_path = pdf_path
        self.reopen_message.setText(
            f"✅ تم إصدار تقرير الـ PDF المعتمد بنجاح!\n"
            f"📁 المسار: {pdf_path}\n"
            f"🖨️ تم فتح تقرير PDF تلقائيًا للطباعة."
        )
        self.reopen_message.setStyleSheet(f"color: {get_color('primary')}; font-weight: bold;")
        self._open_file(pdf_path)

    def reopen_current_order(self):
        if self.current_reopen_order_id is None:
            QMessageBox.warning(self, "تنبيه", "اختر نتيجة معتمدة أولاً لإعادة فتحها")
            return
        reason, ok = QInputDialog.getText(self, "سبب إعادة الفتح", "يرجى كتابة سبب إعادة فتح النتيجة المعتمدة للتعديل:")
        if not ok or not reason.strip():
            QMessageBox.warning(self, "تنبيه", "يجب كتابة سبب لإعادة الفتح")
            return

        from app.ui.patient_history_view import AdminPasswordConfirmDialog
        dlg = AdminPasswordConfirmDialog(self.reopen_title.text(), self)
        if dlg.exec_() == dlg.Accepted:
            password = dlg.get_password().strip()
            if not auth_service.verify_admin_password(password, user_id=self._current_user_id()):
                QMessageBox.warning(self, "خطأ", "كلمة سر الأدمن غير صحيحة! تعذر إعادة فتح النتيجة.")
                return
            
            success, msg = result_service.reopen_reviewed_order(self.current_reopen_order_id, user_id=self._current_user_id(), reason=reason.strip())
            if success:
                QMessageBox.information(self, "تمت العملية", msg)
                self.refresh()
            else:
                QMessageBox.critical(self, "خطأ", msg)

