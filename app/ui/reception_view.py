import subprocess
import sys

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                                QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget, QSpinBox)

from app.reports.barcode_report import generate_sample_labels_pdf
from app.reports.invoice_report import generate_invoice_pdf
from app.services import catalog_service, visit_service
from app.ui.animated_button import AnimatedButton
from app.ui.styles import get_color
from app.ui.widgets import HintBanner, StepLabel


class ReceptionView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        self.selected_tests = []  # list of (test_id, name, price)
        self.search_results = []
        self.doctors = []
        self.sources = []
        self.selected_existing_patient_id = None
        self._phone_matches = []


        outer = QVBoxLayout(self)
        title = QLabel("استقبال / تسجيل زيارة جديدة")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "الخطوات: (1) أدخل بيانات المريض يمين الشاشة - لو رقم تليفونه مسجَّل من قبل هيظهر تنبيه "
            "تلقائيًا. (2) ابحث عن التحاليل المطلوبة وأضفها يسار الشاشة. (3) اضغط 'حفظ الزيارة' "
            "لطباعة الفاتورة وملصقات الباركود تلقائيًا."
        ))

        columns = QHBoxLayout()
        outer.addLayout(columns)

        # ---- Patient card ----
        patient_card = QFrame()
        patient_card.setObjectName("Card")
        patient_layout = QVBoxLayout(patient_card)
        patient_layout.addWidget(StepLabel(1, "بيانات المريض"))

        patient_layout.addWidget(QLabel("اسم المريض"))
        self.name_edit = QLineEdit()
        self.name_edit.setToolTip("الاسم الكامل للمريض كما سيظهر في الفاتورة وتقرير النتيجة")
        self.name_edit.setPlaceholderText("مثال: أحمد محمد علي")
        patient_layout.addWidget(self.name_edit)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("اللقب"))
        self.title_combo = QComboBox()
        self.title_combo.setEditable(True)
        self.title_combo.setToolTip("السيد / السيدة / الآنسة... (اختياري، يمكن الكتابة يدويًا)")
        self.title_combo.addItem("")
        self.title_combo.addItems(catalog_service.get_title_suggestions())
        col1.addWidget(self.title_combo)
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("النوع"))
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["ذكر", "أنثى"])
        self.gender_combo.setToolTip("يُستخدَم لتحديد المدى الطبيعي الصحيح لكل تحليل")
        col2.addWidget(self.gender_combo)
        row.addLayout(col1)
        row.addLayout(col2)
        patient_layout.addLayout(row)

        row2 = QHBoxLayout()
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("السن (سنوات)"))
        self.age_spin = QDoubleSpinBox()
        self.age_spin.setRange(0, 120)
        self.age_spin.setToolTip("يُستخدَم أيضًا لتحديد المدى الطبيعي الصحيح لكل تحليل")
        col3.addWidget(self.age_spin)
        col4 = QVBoxLayout()
        col4.addWidget(QLabel("رقم التليفون"))
        self.phone_edit = QLineEdit()
        self.phone_edit.setToolTip("لو المريض راجع المعمل من قبل بنفس الرقم، هيظهر تنبيه تلقائيًا")
        self.phone_edit.setPlaceholderText("اختياري، لكن يساعد في التعرف على المريض لاحقًا")
        self.phone_edit.editingFinished.connect(self.check_existing_patient)
        self.phone_edit.textEdited.connect(self.on_phone_edited_manually)
        col4.addWidget(self.phone_edit)
        row2.addLayout(col3)
        row2.addLayout(col4)
        patient_layout.addLayout(row2)

        self.existing_patient_hint = QLabel("")
        self.existing_patient_hint.setWordWrap(True)
        self.existing_patient_hint.setStyleSheet("color: #146C8E; font-size: 11px;")
        patient_layout.addWidget(self.existing_patient_hint)
        existing_buttons_row = QHBoxLayout()
        self.use_existing_button = QPushButton("استخدام بيانات هذا المريض")
        self.use_existing_button.setToolTip("يملأ الاسم والبيانات تلقائيًا ويربط هذه الزيارة بسجل المريض الحالي")
        self.use_existing_button.setVisible(False)
        self.use_existing_button.clicked.connect(self.use_existing_patient)
        existing_buttons_row.addWidget(self.use_existing_button)
        self.view_history_button = QPushButton("عرض سجله السابق")
        self.view_history_button.setToolTip("يعرض كل زيارات وتحاليل هذا المريض من قبل")
        self.view_history_button.setVisible(False)
        self.view_history_button.clicked.connect(self.view_existing_patient_history)
        existing_buttons_row.addWidget(self.view_history_button)
        patient_layout.addLayout(existing_buttons_row)

        patient_layout.addWidget(QLabel("الطبيب المحوِّل"))
        self.doctor_combo = QComboBox()
        self.doctor_combo.setToolTip("اختياري - الطبيب الذي أحال المريض للمعمل")
        patient_layout.addWidget(self.doctor_combo)

        patient_layout.addWidget(QLabel("جهة الإحالة"))
        self.source_combo = QComboBox()
        self.source_combo.setToolTip("تحدد السعر المطبَّق تلقائيًا على كل تحليل (فردي، تأمين، جهة معينة...)")
        patient_layout.addWidget(self.source_combo)
        patient_layout.addStretch()

        columns.addWidget(patient_card, 1)

        # ---- Tests card ----
        tests_card = QFrame()
        tests_card.setObjectName("Card")
        tests_layout = QVBoxLayout(tests_card)
        tests_layout.addWidget(StepLabel(2, "التحاليل المطلوبة"))

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("اكتب اسم التحليل أو اختصاره (حرفان على الأقل)...")
        self.search_edit.setToolTip("ابحث بالاسم أو الاختصار، مثال: CBC أو صورة دم")
        self.search_edit.textChanged.connect(self.on_search_changed)
        add_button = QPushButton("إضافة")
        add_button.setObjectName("Primary")
        add_button.setToolTip("أضف التحليل المحدَّد من نتائج البحث لقائمة الزيارة (أو انقر عليه مرتين مباشرة)")
        add_button.clicked.connect(self.add_selected_test)
        search_row.addWidget(self.search_edit)
        search_row.addWidget(add_button)
        tests_layout.addLayout(search_row)

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(110)
        tests_layout.addWidget(self.results_list)

        tests_layout.addWidget(QLabel("التحاليل المضافة لهذه الزيارة:"))
        self.selected_list = QListWidget()
        self.selected_list.setMinimumHeight(140)
        tests_layout.addWidget(self.selected_list)

        remove_button = QPushButton("حذف التحليل المحدد")
        remove_button.setToolTip("يحذف التحليل المحدَّد في القائمة أعلاه من هذه الزيارة")
        remove_button.clicked.connect(self.remove_selected_test)
        tests_layout.addWidget(remove_button)

        tests_layout.addWidget(StepLabel(3, "الدفع والحفظ"))
        totals_row = QHBoxLayout()
        col5 = QVBoxLayout()
        col5.addWidget(QLabel("الخصم"))
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 100000)
        self.discount_spin.setToolTip("مبلغ الخصم (إن وُجد) يُخصَم من الإجمالي قبل حساب المتبقي")
        self.discount_spin.valueChanged.connect(self.update_totals)
        col5.addWidget(self.discount_spin)
        col6 = QVBoxLayout()
        col6.addWidget(QLabel("المبلغ المدفوع"))
        self.payment_spin = QDoubleSpinBox()
        self.payment_spin.setRange(0, 100000)
        self.payment_spin.setToolTip("المبلغ المدفوع الآن - يمكن استكمال الباقي لاحقًا من شاشة الزيارات والفواتير")
        self.payment_spin.valueChanged.connect(self.update_totals)
        col6.addWidget(self.payment_spin)
        totals_row.addLayout(col5)
        totals_row.addLayout(col6)
        tests_layout.addLayout(totals_row)

        self.total_label = QLabel("الإجمالي: 0.00")
        self.balance_label = QLabel("المتبقي: 0.00")
        self.balance_label.setStyleSheet(f"color: {get_color('danger')}; font-weight: bold;")
        tests_layout.addWidget(self.total_label)
        tests_layout.addWidget(self.balance_label)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        tests_layout.addWidget(self.message_label)

        self.status_banner = QLabel("")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet(f"color: {get_color('primary_text')}; font-size: 11px;")
        tests_layout.addWidget(self.status_banner)

        self.save_button = AnimatedButton("حفظ الزيارة وطباعة الفاتورة")
        self.save_button.setObjectName("Primary")
        self.save_button.setToolTip("يحفظ الزيارة، ويطبع الفاتورة وملصقات باركود العينات تلقائيًا")
        self.save_button.clicked.connect(self.save_visit)
        tests_layout.addWidget(self.save_button)

        columns.addWidget(tests_card, 1)

        self.results_list.itemDoubleClicked.connect(lambda *args: self.add_selected_test())

        self.refresh_lookups()

    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-weight: bold; color: {get_color('primary_text')};")
        return label

    def refresh_lookups(self):
        self.doctors = catalog_service.get_doctors()
        self.doctor_combo.clear()
        self.doctor_combo.addItem("-", None)
        for d in self.doctors:
            self.doctor_combo.addItem(d["full_name"], d["id"])

        self.sources = catalog_service.get_referral_sources()
        self.source_combo.clear()
        for s in self.sources:
            self.source_combo.addItem(s["name"], s["id"])

    def on_search_changed(self, text):
        self.results_list.clear()
        self.search_results = []
        if len(text.strip()) < 1:
            return
        self.search_results = catalog_service.search_tests(text.strip())
        for t in self.search_results:
            self.results_list.addItem(f"{t['name']} ({t.get('abbreviation') or ''})")


    def add_selected_test(self):
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self.search_results):
            return
        test = self.search_results[row]

        # Gender validation checks
        gender = self.gender_combo.currentText().strip()
        tname_upper = (test.get("name") or "").upper()

        # Gender validation: BHCG/Pregnancy tests for male patients
        if gender in ("ذكر", "Male", "male") and any(w in tname_upper or w in (test.get("name") or "") for w in ["BHCG", "PREGNANCY", "حمل"]):
            msg = QMessageBox(self)
            msg.setWindowTitle("تنبيه نوع المريض")
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"تنبيه: التحليل «{test['name']}» مخصص للإناث عادةً، بينما نوع المريض المختار هو «ذكر».\nهل ترغب في الاستمرار وإضافة التحليل؟")
            yes_btn = msg.addButton("نعم، أضف التحليل", QMessageBox.YesRole)
            no_btn = msg.addButton("لا، إلغاء", QMessageBox.NoRole)
            msg.setDefaultButton(no_btn)
            msg.exec_()
            if msg.clickedButton() is not yes_btn:
                return

        # Gender validation: PSA/Prostate tests for female patients
        if gender in ("أنثى", "Female", "female") and any(w in tname_upper or w in (test.get("name") or "") for w in ["PSA", "PROSTATE", "بروستاتا"]):
            msg = QMessageBox(self)
            msg.setWindowTitle("تنبيه نوع المريض")
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"تنبيه: التحليل «{test['name']}» مخصص للذكور عادةً بينما نوع المريضة المختارة هو «أنثى».\nهل ترغب في الاستمرار وإضافة التحليل؟")
            yes_btn = msg.addButton("نعم، أضف التحليل", QMessageBox.YesRole)
            no_btn = msg.addButton("لا، إلغاء", QMessageBox.NoRole)
            msg.setDefaultButton(no_btn)
            msg.exec_()
            if msg.clickedButton() is not yes_btn:
                return

        # Warn if this exact test was already ordered for this same (recognized) patient recently -
        # only meaningful once we know who the patient actually is, i.e. an existing patient match.
        if self.selected_existing_patient_id:
            recent_dates = visit_service.get_recent_test_dates(self.selected_existing_patient_id, test["id"])
            if recent_dates:
                last_date = recent_dates[0][:10]
                msg = QMessageBox(self)
                msg.setWindowTitle("تحليل تم عمله مؤخرًا")
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"تنبيه: هذا المريض عمل تحليل «{test['name']}» بالفعل بتاريخ {last_date} "
                            f"(خلال آخر 3 أيام).\nهل ترغب في إضافته مرة أخرى؟")
                yes_btn = msg.addButton("نعم، أضف التحليل", QMessageBox.YesRole)
                no_btn = msg.addButton("لا، إلغاء", QMessageBox.NoRole)
                msg.setDefaultButton(no_btn)
                msg.exec_()
                if msg.clickedButton() is not yes_btn:
                    return

        source_id = self.source_combo.currentData()
        source_name = next((s["name"] for s in self.sources if s["id"] == source_id), "Individual")
        price = catalog_service.get_price(test["id"], source_name)
        self.selected_tests.append((test["id"], test["name"], price))
        self.selected_list.addItem(f"{test['name']} - {price:.2f}")
        self.search_edit.clear()
        self.results_list.clear()
        self.status_banner.setText(f"تمت إضافة: {test['name']}")
        self.update_totals()

    def remove_selected_test(self):
        row = self.selected_list.currentRow()
        if row < 0:
            return
        self.selected_list.takeItem(row)
        del self.selected_tests[row]
        self.update_totals()

    def update_totals(self):
        total = sum(p for _, _, p in self.selected_tests)
        balance = total - self.discount_spin.value() - self.payment_spin.value()
        self.total_label.setText(f"الإجمالي: {total:.2f}")
        self.balance_label.setText(f"المتبقي: {balance:.2f}")

    def check_existing_patient(self):
        phone = self.phone_edit.text().strip()
        self._phone_matches = visit_service.find_patients_by_phone(phone) if phone else []
        if self._phone_matches:
            names = "، ".join(m["full_name"] for m in self._phone_matches[:3])
            self.existing_patient_hint.setText(f"⚠ يوجد مريض مسجَّل بهذا الرقم من قبل: {names}")
            self.use_existing_button.setVisible(True)
            self.view_history_button.setVisible(True)
        else:
            self.existing_patient_hint.setText("")
            self.use_existing_button.setVisible(False)
            self.view_history_button.setVisible(False)

    def on_phone_edited_manually(self, _text):
        # A fresh manual edit invalidates any previously-selected existing patient match/hint.
        self.selected_existing_patient_id = None
        self.existing_patient_hint.setText("")
        self.use_existing_button.setVisible(False)
        self.view_history_button.setVisible(False)

    def use_existing_patient(self):
        if not self._phone_matches:
            return
        match = self._phone_matches[0]
        self.selected_existing_patient_id = match["id"]
        self.name_edit.setText(match["full_name"] or "")
        if match.get("title"):
            self.title_combo.setCurrentText(match["title"])
        self.gender_combo.setCurrentIndex(0 if match.get("gender") == "Male" else 1)
        if match.get("age_years") is not None:
            self.age_spin.setValue(match["age_years"])
        self.existing_patient_hint.setText(f"تم استخدام بيانات المريض: {match['full_name']} (سيُضاف له زيارة جديدة إلى سجله)")
        self.use_existing_button.setVisible(False)

    def view_existing_patient_history(self):
        if not self._phone_matches:
            return
        match = self._phone_matches[0]
        dialog = PatientHistoryDialog(match["id"], match["full_name"], parent=self)
        dialog.exec_()

    def _current_user_id(self):
        return getattr(self.current_user, "user_id", None) if self.current_user else None

    def save_visit(self):
        if not self.name_edit.text().strip():
            self.message_label.setText("أدخل اسم المريض")
            self.message_label.setStyleSheet(f"color: {get_color('danger')};")
            return
        if not self.selected_tests:
            self.message_label.setText("أضف تحليلًا واحدًا على الأقل")
            self.message_label.setStyleSheet(f"color: {get_color('danger')};")
            return
        if self.phone_edit.text().strip() and not self.phone_edit.text().strip().replace("+", "").replace("-", "").replace(" ", "").isdigit():
            self.message_label.setText("رقم التليفون يجب أن يحتوى على أرقام فقط")
            self.message_label.setStyleSheet(f"color: {get_color('danger')};")
            return

        patient = {
            "full_name": self.name_edit.text().strip(),
            "title": self.title_combo.currentText().strip(),
            "gender": "Male" if self.gender_combo.currentIndex() == 0 else "Female",
            "age_years": self.age_spin.value(),
            "phone": self.phone_edit.text().strip(),
        }
        test_ids = [t[0] for t in self.selected_tests]
        try:
            visit = visit_service.create_visit(
                patient, self.doctor_combo.currentData(), self.source_combo.currentData(),
                test_ids, self.discount_spin.value(), self.payment_spin.value(),
                existing_patient_id=self.selected_existing_patient_id,
                user_id=self._current_user_id(),
            )
        except ValueError as exc:
            self.message_label.setText(str(exc))
            self.message_label.setStyleSheet(f"color: {get_color('danger')};")
            return


        self.message_label.setText("جاري إعداد الفاتورة...")
        self.save_button.setEnabled(False)

        def _build_pdfs():
            details = visit_service.get_visit_details(visit["id"])
            settings = catalog_service.get_lab_settings()
            inv_p = generate_invoice_pdf(details, details["orders"], settings)
            return inv_p

        def _on_done(invoice_path):
            self.save_button.setEnabled(True)
            self.message_label.setText(
                f"تم حفظ الزيارة برقم فاتورة {visit['invoice_number']} بنجاح. "
                "تم فتح الفاتورة تلقائيًا للطباعة."
            )
            self.message_label.setStyleSheet(f"color: {get_color('primary')};")
            self.status_banner.setText(f"تمت إضافة زيارة جديدة للمريض: {patient['full_name']}")
            self._open_file(invoice_path)
            self.reset_form()


        def _on_err(err):
            self.save_button.setEnabled(True)
            self.message_label.setText(f"حدث خطأ أثناء إنشاء التقارير: {err}")
            self.message_label.setStyleSheet(f"color: {get_color('danger')};")

        from app.utils.worker import run_in_background
        run_in_background(_build_pdfs, on_success=_on_done, on_error=_on_err)

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

    def reset_form(self):
        self.name_edit.clear()
        self.title_combo.setCurrentIndex(0)
        self.phone_edit.clear()
        self.age_spin.setValue(0)
        self.gender_combo.setCurrentIndex(0)
        self.selected_tests = []
        self.selected_list.clear()
        self.discount_spin.setValue(0)
        self.payment_spin.setValue(0)
        self.selected_existing_patient_id = None
        self._phone_matches = []
        self.existing_patient_hint.setText("")
        self.use_existing_button.setVisible(False)
        self.view_history_button.setVisible(False)
        self.message_label.setText("")
        self.status_banner.setText("")
        self.update_totals()
