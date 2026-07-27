from PySide2.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                                QListWidget, QPushButton, QCheckBox, QTabWidget, QVBoxLayout, QWidget)

from app.services import catalog_service
from app.ui.widgets import HintBanner

DATA_TYPES = ["Numeric", "Text"]
SEX_OPTIONS = ["Both", "Male", "Female"]


class CatalogView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        outer = QVBoxLayout(self)
        title = QLabel("كتالوج التحاليل والإعدادات")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "هنا تتحكم في كل بيانات التحاليل: «التحاليل والأسعار والمعايير» لتعديل تحليل موجود، "
            "«تحليل جديد» لإضافة تحليل من الصفر، «الأقسام» لتصنيف التحاليل (كيمياء، هيماتولوجي...)، "
            "و«الأطباء وجهات الإحالة» لإدارة قوائم الاستقبال."
        ))

        tabs = QTabWidget()
        outer.addWidget(tabs)
        tabs.addTab(self._build_tests_tab(), "التحاليل والأسعار والمعايير")
        tabs.addTab(self._build_new_test_tab(), "تحليل جديد")
        tabs.addTab(self._build_departments_tab(), "الأقسام")
        tabs.addTab(self._build_sources_tab(), "الأطباء وجهات الإحالة")

    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold; color: #0B4F6C;")
        return label

    def refresh(self):
        self.refresh_departments()
        self.refresh_doctors_sources()
        self._reload_department_combo()

    # ================= Tests, parameters, ranges, prices =================
    def _build_tests_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # --- Column 1: search ---
        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._label_bold("بحث عن تحليل"))
        search_row = QHBoxLayout()
        self.test_search_edit = QLineEdit()
        self.test_search_edit.setPlaceholderText("اسم التحليل أو الاختصار...")
        search_button = QPushButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search_tests)
        search_row.addWidget(self.test_search_edit)
        search_row.addWidget(search_button)
        left_layout.addLayout(search_row)

        self.include_inactive_check = QCheckBox("إظهار التحاليل المعطَّلة أيضًا")
        self.include_inactive_check.setToolTip("التحاليل المعطَّلة لا تظهر في الاستقبال، لكنها تبقى محفوظة هنا")
        self.include_inactive_check.stateChanged.connect(self.search_tests)
        left_layout.addWidget(self.include_inactive_check)

        self.test_list = QListWidget()
        self.test_list.itemClicked.connect(self.show_test_details)
        left_layout.addWidget(self.test_list)
        layout.addWidget(left, 1)

        # --- Column 2: test details + parameters ---
        middle = QFrame()
        middle.setObjectName("Card")
        middle_layout = QVBoxLayout(middle)
        self.test_details_title = self._label_bold("اختر تحليلًا لعرض تفاصيله")
        middle_layout.addWidget(self.test_details_title)

        edit_row1 = QHBoxLayout()
        edit_row1.addWidget(QLabel("الاسم"))
        self.edit_name = QLineEdit()
        edit_row1.addWidget(self.edit_name)
        middle_layout.addLayout(edit_row1)

        edit_row2 = QHBoxLayout()
        edit_row2.addWidget(QLabel("الاختصار"))
        self.edit_abbr = QLineEdit()
        edit_row2.addWidget(self.edit_abbr)
        edit_row2.addWidget(QLabel("القسم"))
        self.edit_department_combo = QComboBox()
        edit_row2.addWidget(self.edit_department_combo)
        middle_layout.addLayout(edit_row2)

        test_buttons_row = QHBoxLayout()
        save_test_button = QPushButton("حفظ تعديلات التحليل")
        save_test_button.setObjectName("Primary")
        save_test_button.clicked.connect(self.save_test_edits)
        test_buttons_row.addWidget(save_test_button)
        deactivate_test_button = QPushButton("تعطيل التحليل")
        deactivate_test_button.setToolTip("يخفي التحليل من شاشة الاستقبال دون حذف بياناته أو نتائجه السابقة")
        deactivate_test_button.clicked.connect(self.deactivate_selected_test)
        test_buttons_row.addWidget(deactivate_test_button)
        middle_layout.addLayout(test_buttons_row)

        middle_layout.addWidget(self._label_bold("المعايير"))
        self.parameters_list = QListWidget()
        self.parameters_list.setToolTip("اضغط على معيار لعرض وتعديل مداه الطبيعي في العمود الأيمن")
        self.parameters_list.itemClicked.connect(self.show_parameter_ranges)
        self.parameters_list.setMaximumHeight(160)
        middle_layout.addWidget(self.parameters_list)

        param_row = QHBoxLayout()
        self.new_param_name_edit = QLineEdit()
        self.new_param_name_edit.setPlaceholderText("اسم المعيار")
        param_row.addWidget(self.new_param_name_edit)
        self.new_param_unit_edit = QLineEdit()
        self.new_param_unit_edit.setPlaceholderText("الوحدة")
        param_row.addWidget(self.new_param_unit_edit)
        self.new_param_type_combo = QComboBox()
        self.new_param_type_combo.addItems(DATA_TYPES)
        self.new_param_type_combo.setToolTip("Numeric لقيمة رقمية بمدى طبيعي، Text لقيمة نصية حرة")
        param_row.addWidget(self.new_param_type_combo)
        add_param_button = QPushButton("إضافة معيار")
        add_param_button.setObjectName("Primary")
        add_param_button.clicked.connect(self.add_parameter)
        param_row.addWidget(add_param_button)
        middle_layout.addLayout(param_row)
        delete_param_button = QPushButton("حذف المعيار المحدَّد")
        delete_param_button.clicked.connect(self.delete_selected_parameter)
        middle_layout.addWidget(delete_param_button)

        middle_layout.addWidget(self._label_bold("الأسعار"))
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("جهة الإحالة"))
        self.price_source_combo = QComboBox()
        self.price_source_combo.setToolTip("سعر مختلف لكل جهة إحالة - يُطبَّق تلقائيًا في الاستقبال")
        price_row.addWidget(self.price_source_combo)
        price_row.addWidget(QLabel("السعر"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 100000)
        price_row.addWidget(self.price_spin)
        save_price_button = QPushButton("حفظ السعر")
        save_price_button.setObjectName("Primary")
        save_price_button.setToolTip("يحفظ أو يحدِّث سعر هذا التحليل لجهة الإحالة المختارة")
        save_price_button.clicked.connect(self.save_price)
        price_row.addWidget(save_price_button)
        middle_layout.addLayout(price_row)
        self.test_message = QLabel("")
        middle_layout.addWidget(self.test_message)

        layout.addWidget(middle, 2)

        # --- Column 3: reference ranges for the selected parameter ---
        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        self.ranges_title = self._label_bold("اختر معيارًا لعرض مداه الطبيعي")
        right_layout.addWidget(self.ranges_title)
        self.ranges_list = QListWidget()
        right_layout.addWidget(self.ranges_list)

        range_row1 = QHBoxLayout()
        range_row1.addWidget(QLabel("النوع"))
        self.range_sex_combo = QComboBox()
        self.range_sex_combo.addItems(SEX_OPTIONS)
        self.range_sex_combo.setToolTip("اختر Both لو المدى الطبيعي نفسه للذكر والأنثى")
        range_row1.addWidget(self.range_sex_combo)
        right_layout.addLayout(range_row1)

        range_row2 = QHBoxLayout()
        range_row2.addWidget(QLabel("من سن"))
        self.range_age_from = QDoubleSpinBox()
        self.range_age_from.setRange(0, 120)
        range_row2.addWidget(self.range_age_from)
        range_row2.addWidget(QLabel("إلى سن"))
        self.range_age_to = QDoubleSpinBox()
        self.range_age_to.setRange(0, 120)
        self.range_age_to.setValue(120)
        range_row2.addWidget(self.range_age_to)
        right_layout.addLayout(range_row2)

        range_row3 = QHBoxLayout()
        range_row3.addWidget(QLabel("من قيمة"))
        self.range_low = QDoubleSpinBox()
        self.range_low.setRange(-100000, 100000)
        range_row3.addWidget(self.range_low)
        range_row3.addWidget(QLabel("إلى قيمة"))
        self.range_high = QDoubleSpinBox()
        self.range_high.setRange(-100000, 100000)
        range_row3.addWidget(self.range_high)
        right_layout.addLayout(range_row3)

        self.range_normal_text_edit = QLineEdit()
        self.range_normal_text_edit.setPlaceholderText("نص طبيعي (للقيم غير الرقمية، اختياري)")
        self.range_normal_text_edit.setToolTip(
            "استخدم هذا الحقل بدل 'من/إلى قيمة' لو النتيجة الطبيعية نص وليس رقمًا، مثل 'سلبي' أو 'Negative'"
        )
        right_layout.addWidget(self.range_normal_text_edit)

        add_range_button = QPushButton("إضافة مدى طبيعي")
        add_range_button.setObjectName("Primary")
        add_range_button.setToolTip("يضيف مدى طبيعي جديدًا لهذا المعيار حسب النوع والسن المحدَّدين أعلاه")
        add_range_button.clicked.connect(self.add_range)
        right_layout.addWidget(add_range_button)
        delete_range_button = QPushButton("حذف المدى المحدَّد")
        delete_range_button.clicked.connect(self.delete_selected_range)
        right_layout.addWidget(delete_range_button)
        right_layout.addStretch()

        layout.addWidget(right, 2)

        self.selected_test = None
        self.selected_parameter_id = None
        self.test_search_results = []
        self._reload_sources_combo()
        self._reload_department_combo()
        return widget

    def search_tests(self):
        self.test_search_results = catalog_service.search_tests(
            self.test_search_edit.text().strip(), include_inactive=self.include_inactive_check.isChecked()
        )
        self.test_list.clear()
        for t in self.test_search_results:
            suffix = "" if t["is_active"] else " (معطَّل)"
            self.test_list.addItem(f"{t['name']} ({t.get('department_name') or ''}){suffix}")

    def show_test_details(self, item):
        row = self.test_list.row(item)
        test_id = self.test_search_results[row]["id"]
        self._load_test_details(test_id)

    def _load_test_details(self, test_id, reselect_parameter_id=None):
        details = catalog_service.get_test_with_details(test_id)
        self.selected_test = details
        self.selected_parameter_id = None
        self.test_details_title.setText(details["name"])
        self.edit_name.setText(details["name"])
        self.edit_abbr.setText(details.get("abbreviation") or "")
        idx = self.edit_department_combo.findData(details.get("department_id"))
        self.edit_department_combo.setCurrentIndex(idx if idx >= 0 else 0)

        self.parameters_list.clear()
        for p in details["parameters"]:
            self.parameters_list.addItem(f"{p['name']} ({p.get('unit') or ''}) [{p['data_type']}]")

        self.ranges_list.clear()
        self.ranges_title.setText("اختر معيارًا لعرض مداه الطبيعي")
        self.price_spin.setValue(0)
        self.test_message.setText("")

        # Re-select the parameter that was active before this reload (e.g. after adding/deleting
        # one of its reference ranges) so the ranges panel shows the change immediately, instead of
        # going blank and making it look like the add/delete button did nothing.
        if reselect_parameter_id is not None:
            for i, p in enumerate(details["parameters"]):
                if p["id"] == reselect_parameter_id:
                    self.parameters_list.setCurrentRow(i)
                    self.show_parameter_ranges(self.parameters_list.item(i))
                    break

    def save_test_edits(self):
        if self.selected_test is None:
            return
        catalog_service.save_test({
            "id": self.selected_test["id"],
            "name": self.edit_name.text().strip(),
            "abbreviation": self.edit_abbr.text().strip(),
            "department_id": self.edit_department_combo.currentData(),
            "default_unit": self.selected_test.get("default_unit"),
            "turnaround_time": self.selected_test.get("turnaround_time"),
            "collection_instructions": self.selected_test.get("collection_instructions"),
            "is_active": self.selected_test.get("is_active", 1),
        })
        self.test_message.setText("تم حفظ تعديلات التحليل")
        self.test_message.setStyleSheet("color: #146C8E;")
        self.search_tests()
        self._load_test_details(self.selected_test["id"])

    def deactivate_selected_test(self):
        if self.selected_test is None:
            return
        catalog_service.deactivate_test(self.selected_test["id"])
        self.test_message.setText("تم تعطيل التحليل")
        self.test_message.setStyleSheet("color: #C62828;")
        self.search_tests()

    def add_parameter(self):
        if self.selected_test is None:
            return
        name = self.new_param_name_edit.text().strip()
        if not name:
            return
        catalog_service.save_parameter({
            "test_id": self.selected_test["id"], "name": name,
            "unit": self.new_param_unit_edit.text().strip() or None,
            "data_type": self.new_param_type_combo.currentText(),
        })
        self.new_param_name_edit.clear()
        self.new_param_unit_edit.clear()
        self._load_test_details(self.selected_test["id"])

    def delete_selected_parameter(self):
        if self.selected_parameter_id is None:
            return
        catalog_service.delete_parameter(self.selected_parameter_id)
        self._load_test_details(self.selected_test["id"])

    def show_parameter_ranges(self, item):
        row = self.parameters_list.row(item)
        param = self.selected_test["parameters"][row]
        self.selected_parameter_id = param["id"]
        self.ranges_title.setText(f"المدى الطبيعي: {param['name']}")
        self.ranges_list.clear()
        self._current_ranges = param["ranges"]
        for r in param["ranges"]:
            if r["low_value"] is not None:
                value_text = f"{r['low_value']} - {r['high_value']}"
            else:
                value_text = r.get("normal_text") or ""
            self.ranges_list.addItem(f"{r['sex']} | {r['age_from_years']}-{r['age_to_years']} سنة | {value_text}")

    def add_range(self):
        if self.selected_parameter_id is None:
            return
        parameter_id = self.selected_parameter_id
        normal_text = self.range_normal_text_edit.text().strip() or None
        low = self.range_low.value() if not normal_text else None
        high = self.range_high.value() if not normal_text else None
        catalog_service.save_reference_range({
            "parameter_id": parameter_id,
            "sex": self.range_sex_combo.currentText(),
            "age_from_years": self.range_age_from.value(),
            "age_to_years": self.range_age_to.value(),
            "low_value": low, "high_value": high, "normal_text": normal_text,
        })
        self.range_normal_text_edit.clear()
        self._load_test_details(self.selected_test["id"], reselect_parameter_id=parameter_id)

    def delete_selected_range(self):
        row = self.ranges_list.currentRow()
        if row < 0 or not getattr(self, "_current_ranges", None):
            return
        range_id = self._current_ranges[row]["id"]
        parameter_id = self.selected_parameter_id
        catalog_service.delete_reference_range(range_id)
        self._load_test_details(self.selected_test["id"], reselect_parameter_id=parameter_id)

    def _reload_sources_combo(self):
        self.price_source_combo.clear()
        for s in catalog_service.get_referral_sources():
            self.price_source_combo.addItem(s["name"])

    def _reload_department_combo(self):
        current = getattr(self, "edit_department_combo", None)
        combos = [c for c in [getattr(self, "edit_department_combo", None),
                               getattr(self, "new_test_department_combo", None)] if c is not None]
        for combo in combos:
            combo.clear()
            combo.addItem("-", None)
            for d in catalog_service.get_departments():
                combo.addItem(d["name"], d["id"])

    def save_price(self):
        if self.selected_test is None:
            return
        catalog_service.save_price({
            "test_id": self.selected_test["id"],
            "source_type": self.price_source_combo.currentText(),
            "price": self.price_spin.value(),
        })
        self.test_message.setText("تم حفظ السعر")
        self.test_message.setStyleSheet("color: #146C8E;")

    # ================= New test =================
    def _build_new_test_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = QFrame()
        card.setObjectName("Card")
        form = QVBoxLayout(card)
        form.addWidget(self._label_bold("إضافة تحليل جديد بالكامل"))

        form.addWidget(QLabel("اسم التحليل"))
        self.new_test_name_edit = QLineEdit()
        form.addWidget(self.new_test_name_edit)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("الاختصار"))
        self.new_test_abbr_edit = QLineEdit()
        col1.addWidget(self.new_test_abbr_edit)
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("القسم"))
        self.new_test_department_combo = QComboBox()
        col2.addWidget(self.new_test_department_combo)
        row.addLayout(col1)
        row.addLayout(col2)
        form.addLayout(row)

        form.addWidget(QLabel("الوحدة الافتراضية (اختياري)"))
        self.new_test_unit_edit = QLineEdit()
        form.addWidget(self.new_test_unit_edit)

        create_button = QPushButton("إنشاء التحليل")
        create_button.setObjectName("Primary")
        create_button.clicked.connect(self.create_new_test)
        form.addWidget(create_button)
        self.new_test_message = QLabel("")
        form.addWidget(self.new_test_message)
        form.addStretch()

        layout.addWidget(card)
        self._reload_department_combo()
        return widget

    def create_new_test(self):
        name = self.new_test_name_edit.text().strip()
        if not name:
            self.new_test_message.setText("أدخل اسم التحليل")
            self.new_test_message.setStyleSheet("color: #C62828;")
            return
        test_id = catalog_service.save_test({
            "name": name,
            "abbreviation": self.new_test_abbr_edit.text().strip() or name[:30],
            "department_id": self.new_test_department_combo.currentData(),
            "default_unit": self.new_test_unit_edit.text().strip() or None,
        })
        # Every test needs at least one parameter to be usable in result entry.
        catalog_service.save_parameter({"test_id": test_id, "name": "النتيجة", "data_type": "Text"})
        self.new_test_message.setText(f"تم إنشاء التحليل بنجاح (رقم {test_id}). عدّل معاييره من تبويب «التحاليل والأسعار والمعايير».")
        self.new_test_message.setStyleSheet("color: #146C8E;")
        self.new_test_name_edit.clear()
        self.new_test_abbr_edit.clear()
        self.new_test_unit_edit.clear()

    # ================= Departments =================
    def _build_departments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        add_row = QHBoxLayout()
        self.new_department_edit = QLineEdit()
        self.new_department_edit.setPlaceholderText("اسم القسم الجديد")
        add_button = QPushButton("إضافة")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_department)
        add_row.addWidget(self.new_department_edit)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        self.departments_list = QListWidget()
        layout.addWidget(self.departments_list)
        delete_dept_button = QPushButton("حذف القسم المحدَّد")
        delete_dept_button.setToolTip("لا يمكن حذف قسم مرتبط بتحاليل موجودة - عدِّل قسم كل تحليل أولًا")
        delete_dept_button.clicked.connect(self.delete_selected_department)
        layout.addWidget(delete_dept_button)
        self.department_message = QLabel("")
        layout.addWidget(self.department_message)

        self._departments = []
        self.refresh_departments()
        return widget

    def refresh_departments(self):
        self._departments = catalog_service.get_departments()
        self.departments_list.clear()
        for d in self._departments:
            self.departments_list.addItem(d["name"])

    def add_department(self):
        name = self.new_department_edit.text().strip()
        if not name:
            return
        catalog_service.save_department({"name": name})
        self.new_department_edit.clear()
        self.refresh_departments()
        self._reload_department_combo()

    def delete_selected_department(self):
        row = self.departments_list.currentRow()
        if row < 0:
            return
        department_id = self._departments[row]["id"]
        ok, message = catalog_service.delete_department(department_id)
        self.department_message.setText(message)
        self.department_message.setStyleSheet("color: #146C8E;" if ok else "color: #C62828;")
        if ok:
            self.refresh_departments()
            self._reload_department_combo()

    # ================= Doctors & referral sources =================
    def _build_sources_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        doctors_box = QFrame()
        doctors_box.setObjectName("Card")
        doctors_layout = QVBoxLayout(doctors_box)
        doctors_layout.addWidget(self._label_bold("الأطباء المحوِّلون"))
        doc_row = QHBoxLayout()
        self.new_doctor_edit = QLineEdit()
        self.new_doctor_edit.setPlaceholderText("اسم الطبيب الجديد")
        doc_add = QPushButton("إضافة")
        doc_add.setObjectName("Primary")
        doc_add.clicked.connect(self.add_doctor)
        doc_row.addWidget(self.new_doctor_edit)
        doc_row.addWidget(doc_add)
        doctors_layout.addLayout(doc_row)
        self.doctors_list = QListWidget()
        doctors_layout.addWidget(self.doctors_list)
        deactivate_doctor_button = QPushButton("تعطيل الطبيب المحدَّد")
        deactivate_doctor_button.setToolTip("يخفي الطبيب من قائمة الاستقبال دون حذف زياراته السابقة")
        deactivate_doctor_button.clicked.connect(self.deactivate_selected_doctor)
        doctors_layout.addWidget(deactivate_doctor_button)
        layout.addWidget(doctors_box)

        sources_box = QFrame()
        sources_box.setObjectName("Card")
        sources_layout = QVBoxLayout(sources_box)
        sources_layout.addWidget(self._label_bold("جهات الإحالة"))
        src_row = QHBoxLayout()
        self.new_source_edit = QLineEdit()
        self.new_source_edit.setPlaceholderText("اسم جهة الإحالة الجديدة")
        src_add = QPushButton("إضافة")
        src_add.setObjectName("Primary")
        src_add.clicked.connect(self.add_source)
        src_row.addWidget(self.new_source_edit)
        src_row.addWidget(src_add)
        sources_layout.addLayout(src_row)
        self.sources_list = QListWidget()
        sources_layout.addWidget(self.sources_list)
        deactivate_source_button = QPushButton("تعطيل جهة الإحالة المحدَّدة")
        deactivate_source_button.clicked.connect(self.deactivate_selected_source)
        sources_layout.addWidget(deactivate_source_button)
        layout.addWidget(sources_box)

        self._doctors = []
        self._sources = []
        self.refresh_doctors_sources()
        return widget

    def refresh_doctors_sources(self):
        self._doctors = catalog_service.get_doctors()
        self.doctors_list.clear()
        for d in self._doctors:
            self.doctors_list.addItem(d["full_name"])
        self._sources = catalog_service.get_referral_sources()
        self.sources_list.clear()
        for s in self._sources:
            self.sources_list.addItem(s["name"])

    def add_doctor(self):
        name = self.new_doctor_edit.text().strip()
        if not name:
            return
        catalog_service.save_doctor(name)
        self.new_doctor_edit.clear()
        self.refresh_doctors_sources()

    def deactivate_selected_doctor(self):
        row = self.doctors_list.currentRow()
        if row < 0:
            return
        catalog_service.deactivate_doctor(self._doctors[row]["id"])
        self.refresh_doctors_sources()

    def add_source(self):
        name = self.new_source_edit.text().strip()
        if not name:
            return
        catalog_service.save_referral_source(name)
        self.new_source_edit.clear()
        self.refresh_doctors_sources()
        self._reload_sources_combo()

    def deactivate_selected_source(self):
        row = self.sources_list.currentRow()
        if row < 0:
            return
        catalog_service.deactivate_referral_source(self._sources[row]["id"])
        self.refresh_doctors_sources()
        self._reload_sources_combo()
