from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget
)

from app.services import catalog_service
from app.ui.animated_button import AnimatedButton
from app.ui.styles import get_color
from app.ui.widgets import HintBanner

DATA_TYPES = ["Numeric", "Text"]
SEX_OPTIONS = ["Both", "Male", "Female"]

class CatalogView(QWidget):
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        outer = QVBoxLayout(self)
        
        title = QLabel("📋 كتالوج التحاليل وإدارة النظام")
        title.setObjectName("PageTitle")
        outer.addWidget(title)

        self.catalog_header_hint = HintBanner(
            "تتيح لك هذه الشاشة إدارة كتالوج التحاليل بالكامل: تعديل الأسماء والأقسام، إضافة وتحديد المعايير والمدى الطبيعي، "
            "ضبط أسعار جهات الإحالة المختلفة، وإدارة قوائم الأطباء والأقسام الطبية."
        )
        self.catalog_header_hint.setObjectName("HintBanner")

        outer.addWidget(self.catalog_header_hint)

        tabs = QTabWidget()
        outer.addWidget(tabs)
        tabs.addTab(self._build_tests_tab(), "🧪 التحاليل والأسعار والمعايير")
        tabs.addTab(self._build_new_test_tab(), "➕ تحليل جديد")
        tabs.addTab(self._build_departments_tab(), "🏛️ الأقسام الطبية")
        tabs.addTab(self._build_sources_tab(), "👨‍⚕️ الأطباء وجهات الإحالة")

    def _build_summary_card(self, title: str, value: str, subtitle: str = "") -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(f"background-color: {get_color('bg_card')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 4px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-size: 11px; color: {get_color('primary_text')}; font-weight: 700;")
        value_label = QLabel(value)
        value_label.setObjectName("SummaryValueLabel")
        value_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {get_color('primary_text')};")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.value_label = value_label
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet(f"font-size: 10px; color: {get_color('text_muted')}; font-weight: 600;")
            layout.addWidget(subtitle_label)
        return card

    def _label_bold(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"font-weight: bold; color: {get_color('primary_text')}; font-size: 14px;")
        return label

    def refresh(self):
        self.refresh_departments()
        self.refresh_doctors_sources()
        self._reload_department_combo()
        self.search_tests()

    # ================= Tests, parameters, ranges, prices =================
    def _build_tests_tab(self):
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(10)

        # ================= LEFT COLUMN: SEARCH & TEST LIST (~48%) =================
        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        left_layout.setSpacing(8)

        left_layout.addWidget(self._label_bold("🔍 قائمة التحاليل والاختبارات"))

        # Summary stats cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(6)
        self.stats_cards = [
            self._build_summary_card("إجمالي التحاليل", "0", "كل المسجل"),
            self._build_summary_card("نشط 🟢", "0", "متاح بالاستقبال"),
            self._build_summary_card("معطّل 🔴", "0", "غير ظاهر"),
        ]
        for card in self.stats_cards:
            stats_row.addWidget(card, 1)
        left_layout.addLayout(stats_row)

        # Filter bar
        filter_box = QFrame()
        filter_box.setStyleSheet(f"background-color: {get_color('bg_subtle')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 8px;")
        filter_layout = QVBoxLayout(filter_box)
        filter_layout.setSpacing(6)

        search_row = QHBoxLayout()
        self.test_search_edit = QLineEdit()
        self.test_search_edit.setPlaceholderText("🔍 اسم التحليل أو الاختصار...")
        self.test_search_edit.setStyleSheet(f"padding: 6px 10px; border-radius: 6px; border: 1px solid {get_color('border')}; font-size: 13px; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        self.test_search_edit.returnPressed.connect(self.search_tests)

        search_button = QPushButton("بحث")
        search_button.setObjectName("Primary")
        search_button.clicked.connect(self.search_tests)
        search_row.addWidget(self.test_search_edit, 3)
        search_row.addWidget(search_button, 1)
        filter_layout.addLayout(search_row)

        dept_row = QHBoxLayout()
        dept_row.addWidget(QLabel("القسم:"))
        self.filter_dept_combo = QComboBox()
        self.filter_dept_combo.setStyleSheet(f"padding: 4px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        self.filter_dept_combo.currentIndexChanged.connect(self.search_tests)
        dept_row.addWidget(self.filter_dept_combo, 1)

        self.include_inactive_check = QCheckBox("إظهار المعطَّلة")
        self.include_inactive_check.setToolTip("التحاليل المعطَّلة لا تظهر في الاستقبال")
        self.include_inactive_check.stateChanged.connect(self.search_tests)
        dept_row.addWidget(self.include_inactive_check)

        filter_layout.addLayout(dept_row)
        left_layout.addWidget(filter_box)

        # Tests Table
        self.test_table = QTableWidget()
        self.test_table.setColumnCount(4)
        self.test_table.setHorizontalHeaderLabels(["اسم التحليل", "الاختصار", "القسم", "الحالة"])
        
        self.test_table.horizontalHeader().setFixedHeight(36)
        self.test_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.test_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.test_table.setColumnWidth(1, 90)
        self.test_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.test_table.setColumnWidth(2, 90)
        self.test_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.test_table.setColumnWidth(3, 70)

        self.test_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.test_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.test_table.setAlternatingRowColors(True)
        self.test_table.setSortingEnabled(True)
        self.test_table.setShowGrid(False)
        self.test_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.test_table.setCornerButtonEnabled(False)
        self.test_table.verticalHeader().setVisible(False)
        self.test_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {get_color('border')};
                border-radius: 6px;
                gridline-color: {get_color('border')};
                font-size: 12px;
                background-color: {get_color('bg_card')};
                color: {get_color('text_main')};
            }}
            QHeaderView::section {{
                background-color: {get_color('primary')};
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 4px;
                font-size: 12px;
                border: none;
            }}
            QTableWidget::item {{
                padding: 6px 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {get_color('accent_bg')};
                color: {get_color('accent')};
                font-weight: bold;
            }}
        """)
        self.test_table.itemClicked.connect(self.show_test_details)
        left_layout.addWidget(self.test_table)

        # Pagination & footer
        foot_row = QHBoxLayout()
        self.test_count_label = QLabel("العدد: 0")
        self.test_count_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 11px;")
        foot_row.addWidget(self.test_count_label)
        
        clear_btn = QPushButton("مسح المرشحات 🔄")
        clear_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        clear_btn.clicked.connect(self._clear_filters)
        foot_row.addStretch()
        foot_row.addWidget(clear_btn)
        left_layout.addLayout(foot_row)

        page_ctrl_row = QHBoxLayout()
        page_ctrl_row.addWidget(QLabel("الصفحة:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["50", "100", "300", "عرض الكل"])
        self.page_size_combo.setCurrentText("300")
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        page_ctrl_row.addWidget(self.page_size_combo)

        self.prev_button = QPushButton("◀ السابق")
        self.prev_button.clicked.connect(lambda: self._change_page(-1))
        page_ctrl_row.addWidget(self.prev_button)

        self.page_label = QLabel("")
        self.page_label.setStyleSheet(f"color: {get_color('text_main')}; font-weight: bold;")
        page_ctrl_row.addWidget(self.page_label)

        self.next_button = QPushButton("التالي ▶")
        self.next_button.clicked.connect(lambda: self._change_page(1))
        page_ctrl_row.addWidget(self.next_button)

        left_layout.addLayout(page_ctrl_row)

        self.page_size = 300
        self.current_page = 1
        self.total_matching = 0
        self.test_list = self.test_table  # Alias

        main_layout.addWidget(left, 48)

        # ================= RIGHT COLUMN: TEST DETAILS PANEL (~60%) =================
        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(10)

        # Header card for selected test
        self.test_details_title = QLabel("👈 اختر تحليلًا من القائمة لعرض وتعديل تفاصيله")
        self.test_details_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0B4F6C;")
        right_layout.addWidget(self.test_details_title)

        # Nested Sub-Tabs for Details
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet("""
            QTabBar::tab {
                font-size: 13px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                color: #0B4F6C;
                border-bottom: 2px solid #0B4F6C;
            }
        """)

        # --- Sub-Tab 1: Basic Info & Prices ---
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setSpacing(12)

        info_group = QFrame()
        info_group.setStyleSheet(f"background-color: {get_color('bg_subtle')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(self._label_bold("⚙️ البيانات الأساسية"))

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("اسم التحليل:"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("اسم التحليل الكامل...")
        self.edit_name.setStyleSheet(f"padding: 6px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        r1.addWidget(self.edit_name, 2)
        r1.addWidget(QLabel("الاختصار:"))
        self.edit_abbr = QLineEdit()
        self.edit_abbr.setPlaceholderText("الاختصار...")
        self.edit_abbr.setStyleSheet(f"padding: 6px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        r1.addWidget(self.edit_abbr, 1)
        info_layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("القسم الطبي:"))
        self.edit_department_combo = QComboBox()
        self.edit_department_combo.setStyleSheet(f"padding: 6px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        r2.addWidget(self.edit_department_combo, 2)
        
        save_test_button = QPushButton("حفظ تعديلات التحليل 💾")
        save_test_button.setObjectName("Primary")
        save_test_button.clicked.connect(self.save_test_edits)
        r2.addWidget(save_test_button, 1)

        self.deactivate_test_button = QPushButton("تعطيل التحليل ⛔")
        self.deactivate_test_button.setObjectName("Danger")
        self.deactivate_test_button.clicked.connect(self.deactivate_selected_test)
        r2.addWidget(self.deactivate_test_button, 1)
        info_layout.addLayout(r2)

        basic_layout.addWidget(info_group)

        # Price group
        price_group = QFrame()
        price_group.setStyleSheet(f"background-color: {get_color('bg_subtle')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 10px;")
        price_layout = QVBoxLayout(price_group)
        price_layout.addWidget(self._label_bold("💰 تسعير جهات الإحالة والمؤسسات"))

        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("جهة الإحالة:"))
        self.price_source_combo = QComboBox()
        self.price_source_combo.setStyleSheet(f"padding: 6px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        p_row.addWidget(self.price_source_combo, 2)

        p_row.addWidget(QLabel("السعر:"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 100000)
        self.price_spin.setSuffix(" ج.م")
        self.price_spin.setStyleSheet(f"padding: 6px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        p_row.addWidget(self.price_spin, 1)

        save_price_button = QPushButton("حفظ السعر 💾")
        save_price_button.setObjectName("Primary")
        save_price_button.clicked.connect(self.save_price)
        p_row.addWidget(save_price_button, 1)

        price_layout.addLayout(p_row)
        basic_layout.addWidget(price_group)

        self.test_message = QLabel("")
        self.test_message.setWordWrap(True)
        basic_layout.addWidget(self.test_message)
        basic_layout.addStretch()

        self.detail_tabs.addTab(basic_tab, "⚙️ البيانات والأسعار")

        # --- Sub-Tab 2: Parameters & Reference Ranges ---
        params_tab = QWidget()
        params_layout = QHBoxLayout(params_tab)
        params_layout.setSpacing(10)

        # Parameters section (left side of params tab - 40%)
        params_box = QFrame()
        params_box.setStyleSheet(f"background-color: {get_color('bg_subtle')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 8px;")
        pb_layout = QVBoxLayout(params_box)
        pb_layout.setSpacing(6)
        pb_layout.addWidget(self._label_bold("📏 المعايير (Parameters)"))

        self.parameters_table = QTableWidget()
        self.parameters_table.setColumnCount(3)
        self.parameters_table.setHorizontalHeaderLabels(["المعيار", "الوحدة", "النوع"])
        self.parameters_table.horizontalHeader().setFixedHeight(36)
        self.parameters_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.parameters_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.parameters_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.parameters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.parameters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.parameters_table.setAlternatingRowColors(True)
        self.parameters_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.parameters_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {get_color('border')};
                border-radius: 6px;
                gridline-color: {get_color('border')};
                font-size: 12px;
                background-color: {get_color('bg_card')};
                color: {get_color('text_main')};
            }}
            QHeaderView::section {{
                background-color: {get_color('primary')};
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 4px;
                font-size: 12px;
                border: none;
            }}
            QTableWidget::item {{
                padding: 6px 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {get_color('accent_bg')};
                color: {get_color('accent')};
                font-weight: bold;
            }}
        """)
        self.parameters_table.itemClicked.connect(self.show_parameter_ranges)
        pb_layout.addWidget(self.parameters_table)

        self.parameters_list = self.parameters_table  # Alias

        param_add_row = QHBoxLayout()
        self.new_param_name_edit = QLineEdit()
        self.new_param_name_edit.setPlaceholderText("اسم المعيار...")
        self.new_param_name_edit.setStyleSheet(f"padding: 5px; border-radius: 4px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        param_add_row.addWidget(self.new_param_name_edit, 2)

        self.new_param_unit_edit = QLineEdit()
        self.new_param_unit_edit.setPlaceholderText("الوحدة...")
        self.new_param_unit_edit.setStyleSheet(f"padding: 5px; border-radius: 4px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        param_add_row.addWidget(self.new_param_unit_edit, 1)

        self.new_param_type_combo = QComboBox()
        self.new_param_type_combo.addItems(DATA_TYPES)
        self.new_param_type_combo.setStyleSheet(f"padding: 5px; border-radius: 4px; border: 1px solid {get_color('border')}; color: {get_color('text_main')}; background-color: {get_color('bg_card')};")
        param_add_row.addWidget(self.new_param_type_combo, 1)

        add_param_btn = QPushButton("إضافة ➕")
        add_param_btn.setObjectName("Primary")
        add_param_btn.clicked.connect(self.add_parameter)
        param_add_row.addWidget(add_param_btn)
        pb_layout.addLayout(param_add_row)

        del_param_btn = QPushButton("حذف المعيار المحدَّد 🗑️")
        del_param_btn.setObjectName("Danger")
        del_param_btn.clicked.connect(self.delete_selected_parameter)
        pb_layout.addWidget(del_param_btn)

        params_layout.addWidget(params_box, 40)

        # Ranges section (right side of params tab - 60%)
        ranges_box = QFrame()
        ranges_box.setStyleSheet(f"background-color: {get_color('bg_subtle')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 8px;")
        rb_layout = QVBoxLayout(ranges_box)
        rb_layout.setSpacing(6)

        self.ranges_title = self._label_bold("📐 المدى الطبيعي للمعيار المختار")
        rb_layout.addWidget(self.ranges_title)

        self.ranges_table = QTableWidget()
        self.ranges_table.setColumnCount(3)
        self.ranges_table.setHorizontalHeaderLabels(["النوع", "السن", "المدى الطبيعي"])
        self.ranges_table.horizontalHeader().setFixedHeight(36)
        self.ranges_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ranges_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.ranges_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.ranges_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ranges_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ranges_table.setAlternatingRowColors(True)
        self.ranges_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ranges_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {get_color('border')};
                border-radius: 6px;
                gridline-color: {get_color('border')};
                font-size: 12px;
                background-color: {get_color('bg_card')};
                color: {get_color('text_main')};
            }}
            QHeaderView::section {{
                background-color: {get_color('primary')};
                color: #FFFFFF;
                font-weight: bold;
                padding: 6px 4px;
                font-size: 12px;
                border: none;
            }}
            QTableWidget::item {{
                padding: 6px 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {get_color('accent_bg')};
                color: {get_color('accent')};
                font-weight: bold;
            }}
        """)
        rb_layout.addWidget(self.ranges_table)

        self.ranges_list = self.ranges_table  # Alias

        range_ctrl_box = QFrame()
        range_ctrl_box.setStyleSheet(f"background-color: {get_color('bg_card')}; border: 1px solid {get_color('border')}; border-radius: 8px; padding: 8px;")
        rc_layout = QVBoxLayout(range_ctrl_box)
        rc_layout.setSpacing(6)

        rc_grid = QGridLayout()
        rc_grid.setSpacing(6)

        input_qss = f"padding: 4px; border-radius: 4px; border: 1px solid {get_color('border')}; color: {get_color('primary_text')}; background-color: {get_color('bg_subtle')}; font-size: 12px;"

        rc_grid.addWidget(QLabel("النوع:"), 0, 0)
        self.range_sex_combo = QComboBox()
        self.range_sex_combo.addItems(SEX_OPTIONS)
        self.range_sex_combo.setStyleSheet(input_qss)
        self.range_sex_combo.setMinimumWidth(75)
        rc_grid.addWidget(self.range_sex_combo, 0, 1)

        rc_grid.addWidget(QLabel("من سن:"), 0, 2)
        self.range_age_from = QDoubleSpinBox()
        self.range_age_from.setRange(0, 120)
        self.range_age_from.setStyleSheet(input_qss)
        self.range_age_from.setMinimumWidth(55)
        rc_grid.addWidget(self.range_age_from, 0, 3)

        rc_grid.addWidget(QLabel("إلى سن:"), 0, 4)
        self.range_age_to = QDoubleSpinBox()
        self.range_age_to.setRange(0, 120)
        self.range_age_to.setValue(120)
        self.range_age_to.setStyleSheet(input_qss)
        self.range_age_to.setMinimumWidth(55)
        rc_grid.addWidget(self.range_age_to, 0, 5)

        rc_grid.addWidget(QLabel("من قيمة:"), 1, 0)
        self.range_low = QDoubleSpinBox()
        self.range_low.setRange(-100000, 100000)
        self.range_low.setStyleSheet(input_qss)
        self.range_low.setMinimumWidth(60)
        rc_grid.addWidget(self.range_low, 1, 1)

        rc_grid.addWidget(QLabel("إلى قيمة:"), 1, 2)
        self.range_high = QDoubleSpinBox()
        self.range_high.setRange(-100000, 100000)
        self.range_high.setStyleSheet(input_qss)
        self.range_high.setMinimumWidth(60)
        rc_grid.addWidget(self.range_high, 1, 3)

        rc_layout.addLayout(rc_grid)

        self.range_normal_text_edit = QLineEdit()
        self.range_normal_text_edit.setPlaceholderText("نص طبيعي للنتائج الكيفية (مثال: سلبي / Negative)...")
        self.range_normal_text_edit.setStyleSheet(f"padding: 6px; border-radius: 6px; border: 1px solid {get_color('border')}; color: {get_color('primary_text')}; background-color: {get_color('bg_subtle')};")
        rc_layout.addWidget(self.range_normal_text_edit)

        r_btns = QHBoxLayout()
        add_range_btn = QPushButton("إضافة مدى ➕")
        add_range_btn.setObjectName("Primary")
        add_range_btn.clicked.connect(self.add_range)
        r_btns.addWidget(add_range_btn)

        del_range_btn = QPushButton("حذف المدى 🗑️")
        del_range_btn.setObjectName("Danger")
        del_range_btn.clicked.connect(self.delete_selected_range)
        r_btns.addWidget(del_range_btn)
        rc_layout.addLayout(r_btns)

        rb_layout.addWidget(range_ctrl_box)
        params_layout.addWidget(ranges_box, 60)

        self.detail_tabs.addTab(params_tab, "📏 المعايير والمدى الطبيعي")

        right_layout.addWidget(self.detail_tabs)

        main_layout.addWidget(right, 52)

        self.selected_test = None
        self.selected_parameter_id = None
        self.test_search_results = []
        self._reload_sources_combo()
        self._reload_department_combo()
        self.search_tests()
        return widget

    def _clear_filters(self):
        if hasattr(self, "test_search_edit"):
            self.test_search_edit.clear()
        if hasattr(self, "filter_dept_combo"):
            self.filter_dept_combo.setCurrentIndex(0)
        if hasattr(self, "include_inactive_check"):
            self.include_inactive_check.setChecked(False)
        self.current_page = 1
        self.search_tests()

    def _load_more_tests(self):
        if self.page_size == 0:
            return
        self.current_page += 1
        self.search_tests()

    def _change_page(self, delta: int):
        if self.page_size == 0:
            return
        total_pages = max(1, (self.total_matching + self.page_size - 1) // self.page_size)
        new_page = max(1, min(total_pages, self.current_page + delta))
        if new_page == self.current_page:
            return
        self.current_page = new_page
        self.search_tests()

    def _on_page_size_changed(self, idx: int):
        text = self.page_size_combo.currentText()
        if text == "عرض الكل":
            self.page_size = 0
        else:
            try:
                self.page_size = int(text)
            except Exception:
                self.page_size = 300
        self.current_page = 1
        self.search_tests()

    def search_tests(self, append: bool = False):
        query = self.test_search_edit.text().strip()
        dept_id = self.filter_dept_combo.currentData() if hasattr(self, "filter_dept_combo") else None
        include_inactive = self.include_inactive_check.isChecked()

        limit = None if self.page_size == 0 else self.page_size
        offset = 0 if self.current_page <= 1 else (self.current_page - 1) * (self.page_size or 0)

        if not append:
            self.test_table.setRowCount(0)

        results = catalog_service.search_tests(
            query, department_id=dept_id, include_inactive=include_inactive,
            limit=limit, offset=offset
        )

        self.test_search_results = results

        for t in results:
            row_idx = self.test_table.rowCount()
            self.test_table.insertRow(row_idx)
            item_name = QTableWidgetItem(t['name'])
            item_name.setTextAlignment(int(Qt.AlignRight) | int(Qt.AlignVCenter))
            self.test_table.setItem(row_idx, 0, item_name)
            item_abbr = QTableWidgetItem(t.get('abbreviation') or "-")
            item_abbr.setTextAlignment(int(Qt.AlignCenter))
            self.test_table.setItem(row_idx, 1, item_abbr)
            item_dept = QTableWidgetItem(t.get('department_name') or "-")
            item_dept.setTextAlignment(int(Qt.AlignCenter))
            self.test_table.setItem(row_idx, 2, item_dept)
            status_text = "🟢 نشط" if t['is_active'] else "🔴 معطَّل"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(int(Qt.AlignCenter))
            if not t['is_active']:
                item_status.setForeground(Qt.red)
            self.test_table.setItem(row_idx, 3, item_status)

        # Update totals and page UI
        self.total_matching = catalog_service.count_tests(query, department_id=dept_id, include_inactive=include_inactive)
        loaded = self.test_table.rowCount()
        if hasattr(self, "test_count_label"):
            self.test_count_label.setText(f"عرض {loaded} من {self.total_matching} نتيجة")

        stats = catalog_service.get_catalog_dashboard_stats()
        if hasattr(self, "stats_cards"):
            self.stats_cards[0].value_label.setText(str(stats["total_tests"]))
            self.stats_cards[1].value_label.setText(str(stats["active_tests"]))
            self.stats_cards[2].value_label.setText(str(stats["inactive_tests"]))

        # Update pagination controls
        if self.page_size == 0:
            # 'عرض الكل' selected
            self.page_label.setText("صفحة 1 من 1")
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
        else:
            total_pages = max(1, (self.total_matching + self.page_size - 1) // self.page_size)
            self.page_label.setText(f"صفحة {self.current_page} من {total_pages}")
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < total_pages)

    def show_test_details(self, *args):
        row = self.test_table.currentRow()
        if row < 0 or row >= len(self.test_search_results):
            return
        test_id = self.test_search_results[row]["id"]
        self._load_test_details(test_id)

    def _load_test_details(self, test_id, reselect_parameter_id=None):
        details = catalog_service.get_test_with_details(test_id)
        if not details:
            return
        self.selected_test = details
        self.selected_parameter_id = None
        
        status_suffix = "" if details.get("is_active", 1) else " (معطَّل)"
        self.test_details_title.setText(f"🧪 {details['name']}{status_suffix}")
        self.edit_name.setText(details["name"])
        self.edit_abbr.setText(details.get("abbreviation") or "")
        
        idx = self.edit_department_combo.findData(details.get("department_id"))
        self.edit_department_combo.setCurrentIndex(idx if idx >= 0 else 0)

        # Update button text according to active status
        if hasattr(self, "deactivate_test_button"):
            if details.get("is_active", 1):
                self.deactivate_test_button.setText("تعطيل التحليل ⛔")
            else:
                self.deactivate_test_button.setText("إعادة تفعيل التحليل ❇️")

        # Load parameters into parameters_table
        self.parameters_table.setRowCount(0)
        for row_idx, p in enumerate(details["parameters"]):
            self.parameters_table.insertRow(row_idx)
            
            item_pname = QTableWidgetItem(p['name'])
            item_pname.setTextAlignment(int(Qt.AlignRight) | int(Qt.AlignVCenter))
            self.parameters_table.setItem(row_idx, 0, item_pname)
            
            item_punit = QTableWidgetItem(p.get('unit') or "-")
            item_punit.setTextAlignment(int(Qt.AlignCenter))
            self.parameters_table.setItem(row_idx, 1, item_punit)
            
            type_label = "رقمي 🔢" if p['data_type'] == 'Numeric' else "نصي 📝"
            item_ptype = QTableWidgetItem(type_label)
            item_ptype.setTextAlignment(int(Qt.AlignCenter))
            self.parameters_table.setItem(row_idx, 2, item_ptype)

        self.ranges_table.setRowCount(0)
        self.ranges_title.setText("اختر معيارًا لعرض مداه الطبيعي")
        self.price_spin.setValue(0)
        self.test_message.setText("")

        if reselect_parameter_id is not None:
            for i, p in enumerate(details["parameters"]):
                if p["id"] == reselect_parameter_id:
                    self.parameters_table.setCurrentCell(i, 0)
                    self.show_parameter_ranges()
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
        self.test_message.setText("تم حفظ تعديلات التحليل بنجاح")
        self.test_message.setStyleSheet("color: #146C8E;")
        self.search_tests()
        self._load_test_details(self.selected_test["id"])

    def deactivate_selected_test(self):
        if self.selected_test is None:
            return
        current_status = self.selected_test.get("is_active", 1)
        if current_status:
            catalog_service.deactivate_test(self.selected_test["id"])
            self.test_message.setText("تم تعطيل التحليل بنجاح")
            self.test_message.setStyleSheet("color: #C62828;")
        else:
            self.selected_test["is_active"] = 1
            catalog_service.save_test(self.selected_test)
            self.test_message.setText("تمت إعادة تفعيل التحليل بنجاح")
            self.test_message.setStyleSheet("color: #146C8E;")
        self.search_tests()
        self._load_test_details(self.selected_test["id"])

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
        row = self.parameters_table.currentRow()
        if row < 0 or self.selected_test is None or row >= len(self.selected_test["parameters"]):
            return
        param_id = self.selected_test["parameters"][row]["id"]
        catalog_service.delete_parameter(param_id)
        self._load_test_details(self.selected_test["id"])

    def show_parameter_ranges(self, *args):
        row = self.parameters_table.currentRow()
        if row < 0 or self.selected_test is None or row >= len(self.selected_test["parameters"]):
            return
        param = self.selected_test["parameters"][row]
        self.selected_parameter_id = param["id"]
        self.ranges_title.setText(f"📐 المدى الطبيعي للمعيار: {param['name']}")
        
        self.ranges_table.setRowCount(0)
        self._current_ranges = param["ranges"]
        for row_idx, r in enumerate(param["ranges"]):
            self.ranges_table.insertRow(row_idx)
            
            sex_map = {"Both": "الجميع 🚻", "Male": "ذكور ♂️", "Female": "إناث ♀️"}
            sex_str = sex_map.get(r['sex'], r['sex'])
            item_sex = QTableWidgetItem(sex_str)
            item_sex.setTextAlignment(int(Qt.AlignCenter))
            self.ranges_table.setItem(row_idx, 0, item_sex)
            
            age_str = f"{r['age_from_years']} - {r['age_to_years']} سنة"
            item_age = QTableWidgetItem(age_str)
            item_age.setTextAlignment(int(Qt.AlignCenter))
            self.ranges_table.setItem(row_idx, 1, item_age)
            
            if r["low_value"] is not None:
                # A plain "-" separator (not the Arabic word "إلى") is used deliberately: mixing an
                # RTL word directly between two LTR numeric runs makes Qt's bidi algorithm reorder
                # the numbers unpredictably in an RTL-direction table cell (e.g. "4.0 11.0 إلى"
                # instead of "4.0 إلى 11.0") - this is the exact "range text overlapping/jumbled"
                # bug reported for this table. Every other range display in the app (results
                # entry, PDF reports) already uses "-" for this same reason.
                val_str = f"{r['low_value']} - {r['high_value']}"
            else:
                val_str = r.get("normal_text") or "-"
            item_val = QTableWidgetItem(val_str)
            item_val.setTextAlignment(int(Qt.AlignCenter))
            self.ranges_table.setItem(row_idx, 2, item_val)

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
        row = self.ranges_table.currentRow()
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
        depts = catalog_service.get_departments()
        
        # Filter combo in search bar
        if hasattr(self, "filter_dept_combo"):
            curr_data = self.filter_dept_combo.currentData()
            self.filter_dept_combo.blockSignals(True)
            self.filter_dept_combo.clear()
            self.filter_dept_combo.addItem("جميع الأقسام 🏛️", None)
            for d in depts:
                self.filter_dept_combo.addItem(d["name"], d["id"])
            idx = self.filter_dept_combo.findData(curr_data)
            self.filter_dept_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.filter_dept_combo.blockSignals(False)

        # Edit and new test combos
        combos = [c for c in [getattr(self, "edit_department_combo", None),
                               getattr(self, "new_test_department_combo", None)] if c is not None]
        for combo in combos:
            curr_data = combo.currentData()
            combo.clear()
            combo.addItem("- بدون قسم -", None)
            for d in depts:
                combo.addItem(d["name"], d["id"])
            idx = combo.findData(curr_data)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def save_price(self):
        if self.selected_test is None:
            return
        catalog_service.save_price({
            "test_id": self.selected_test["id"],
            "source_type": self.price_source_combo.currentText(),
            "price": self.price_spin.value(),
        })
        self.test_message.setText("تم حفظ السعر بنجاح")
        self.test_message.setStyleSheet("color: #146C8E;")

    # ================= New test =================
    def _build_new_test_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        card = QFrame()
        card.setObjectName("Card")
        form = QVBoxLayout(card)
        form.addWidget(self._label_bold("➕ إضافة تحليل جديد بالكامل"))

        form.addWidget(QLabel("اسم التحليل:"))
        self.new_test_name_edit = QLineEdit()
        self.new_test_name_edit.setPlaceholderText("مثال: Complete Blood Count")
        form.addWidget(self.new_test_name_edit)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("الاختصار:"))
        self.new_test_abbr_edit = QLineEdit()
        self.new_test_abbr_edit.setPlaceholderText("مثال: CBC")
        col1.addWidget(self.new_test_abbr_edit)
        
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("القسم الطبي:"))
        self.new_test_department_combo = QComboBox()
        col2.addWidget(self.new_test_department_combo)
        
        row.addLayout(col1)
        row.addLayout(col2)
        form.addLayout(row)

        form.addWidget(QLabel("الوحدة الافتراضية (اختياري):"))
        self.new_test_unit_edit = QLineEdit()
        self.new_test_unit_edit.setPlaceholderText("مثال: mg/dL, g/dL, %")
        form.addWidget(self.new_test_unit_edit)

        create_button = QPushButton("إنشاء التحليل 🚀")
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
            self.new_test_message.setText("برجاء إدخال اسم التحليل")
            self.new_test_message.setStyleSheet("color: #C62828;")
            return
        test_id = catalog_service.save_test({
            "name": name,
            "abbreviation": self.new_test_abbr_edit.text().strip() or name[:30],
            "department_id": self.new_test_department_combo.currentData(),
            "default_unit": self.new_test_unit_edit.text().strip() or None,
        })
        catalog_service.save_parameter({"test_id": test_id, "name": "النتيجة", "data_type": "Text"})
        self.new_test_message.setText(f"تم إنشاء التحليل بنجاح (رقم {test_id}). يمكنك إضافة المعايير والأسعار من تبويب «التحاليل والأسعار والمعايير».")
        self.new_test_message.setStyleSheet("color: #146C8E;")
        self.new_test_name_edit.clear()
        self.new_test_abbr_edit.clear()
        self.new_test_unit_edit.clear()
        self.search_tests()

    # ================= Departments =================
    def _build_departments_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(self._label_bold("🏛️ إدارة الأقسام الطبية"))

        add_row = QHBoxLayout()
        self.new_department_edit = QLineEdit()
        self.new_department_edit.setPlaceholderText("اسم القسم الجديد (مثال: كيمياء الدم، الهيماتولوجي...)")
        add_button = QPushButton("إضافة قسم ➕")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_department)
        add_row.addWidget(self.new_department_edit, 3)
        add_row.addWidget(add_button, 1)
        card_layout.addLayout(add_row)

        self.departments_table = QTableWidget()
        self.departments_table.setColumnCount(2)
        self.departments_table.setHorizontalHeaderLabels(["#", "اسم القسم"])
        self.departments_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.departments_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.departments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.departments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.departments_table.setAlternatingRowColors(True)
        card_layout.addWidget(self.departments_table)

        # Alias for backward compatibility
        self.departments_list = self.departments_table

        delete_dept_button = QPushButton("حذف القسم المحدَّد 🗑️")
        delete_dept_button.setObjectName("Danger")
        delete_dept_button.setToolTip("لا يمكن حذف قسم مرتبط بتحاليل موجودة - عدِّل قسم كل تحليل أولًا")
        delete_dept_button.clicked.connect(self.delete_selected_department)
        card_layout.addWidget(delete_dept_button)
        
        self.department_message = QLabel("")
        card_layout.addWidget(self.department_message)

        layout.addWidget(card)

        self._departments = []
        self.refresh_departments()
        return widget

    def refresh_departments(self):
        self._departments = catalog_service.get_departments()
        self.departments_table.setRowCount(0)
        for row_idx, d in enumerate(self._departments):
            self.departments_table.insertRow(row_idx)
            
            item_id = QTableWidgetItem(str(d["id"]))
            item_id.setTextAlignment(int(Qt.AlignCenter))
            self.departments_table.setItem(row_idx, 0, item_id)
            
            item_name = QTableWidgetItem(d["name"])
            item_name.setTextAlignment(int(Qt.AlignRight) | int(Qt.AlignVCenter))
            self.departments_table.setItem(row_idx, 1, item_name)

    def add_department(self):
        name = self.new_department_edit.text().strip()
        if not name:
            return
        catalog_service.save_department({"name": name})
        self.new_department_edit.clear()
        self.refresh_departments()
        self._reload_department_combo()

    def delete_selected_department(self):
        row = self.departments_table.currentRow()
        if row < 0 or row >= len(self._departments):
            return
        department_id = self._departments[row]["id"]
        ok, message = catalog_service.delete_department(department_id)
        self.department_message.setText(message)
        self.department_message.setStyleSheet("color: #146C8E;" if ok else "color: #C62828;")
        if ok:
            self.refresh_departments()
            self._reload_department_combo()

    # ================= Doctors & Referral Sources =================
    def _build_sources_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Doctors Box
        doctors_box = QFrame()
        doctors_box.setObjectName("Card")
        doctors_layout = QVBoxLayout(doctors_box)
        doctors_layout.addWidget(self._label_bold("👨‍⚕️ الأطباء المحوِّلون"))
        
        doc_row = QHBoxLayout()
        self.new_doctor_edit = QLineEdit()
        self.new_doctor_edit.setPlaceholderText("اسم الطبيب الجديد...")
        doc_add = QPushButton("إضافة ➕")
        doc_add.setObjectName("Primary")
        doc_add.clicked.connect(self.add_doctor)
        doc_row.addWidget(self.new_doctor_edit)
        doc_row.addWidget(doc_add)
        doctors_layout.addLayout(doc_row)

        self.doctors_table = QTableWidget()
        self.doctors_table.setColumnCount(2)
        self.doctors_table.setHorizontalHeaderLabels(["#", "اسم الطبيب"])
        self.doctors_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.doctors_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doctors_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doctors_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.doctors_table.setAlternatingRowColors(True)
        doctors_layout.addWidget(self.doctors_table)

        # Alias for backward compatibility
        self.doctors_list = self.doctors_table

        deactivate_doctor_button = QPushButton("تعطيل الطبيب المحدَّد ⛔")
        deactivate_doctor_button.setObjectName("Danger")
        deactivate_doctor_button.setToolTip("يخفي الطبيب من قائمة الاستقبال دون حذف زياراته السابقة")
        deactivate_doctor_button.clicked.connect(self.deactivate_selected_doctor)
        doctors_layout.addWidget(deactivate_doctor_button)
        layout.addWidget(doctors_box)

        # Referral Sources Box
        sources_box = QFrame()
        sources_box.setObjectName("Card")
        sources_layout = QVBoxLayout(sources_box)
        sources_layout.addWidget(self._label_bold("🏢 جهات الإحالة والمؤسسات"))
        
        src_row = QHBoxLayout()
        self.new_source_edit = QLineEdit()
        self.new_source_edit.setPlaceholderText("اسم جهة الإحالة الجديدة...")
        src_add = QPushButton("إضافة ➕")
        src_add.setObjectName("Primary")
        src_add.clicked.connect(self.add_source)
        src_row.addWidget(self.new_source_edit)
        src_row.addWidget(src_add)
        sources_layout.addLayout(src_row)

        self.sources_table = QTableWidget()
        self.sources_table.setColumnCount(2)
        self.sources_table.setHorizontalHeaderLabels(["#", "اسم الجهة"])
        self.sources_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.sources_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sources_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sources_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sources_table.setAlternatingRowColors(True)
        sources_layout.addWidget(self.sources_table)

        # Alias for backward compatibility
        self.sources_list = self.sources_table

        deactivate_source_button = QPushButton("تعطيل جهة الإحالة المحدَّدة ⛔")
        deactivate_source_button.setObjectName("Danger")
        deactivate_source_button.clicked.connect(self.deactivate_selected_source)
        sources_layout.addWidget(deactivate_source_button)
        layout.addWidget(sources_box)

        self._doctors = []
        self._sources = []
        self.refresh_doctors_sources()
        return widget

    def refresh_doctors_sources(self):
        self._doctors = catalog_service.get_doctors()
        self.doctors_table.setRowCount(0)
        for row_idx, d in enumerate(self._doctors):
            self.doctors_table.insertRow(row_idx)
            
            item_id = QTableWidgetItem(str(d["id"]))
            item_id.setTextAlignment(int(Qt.AlignCenter))
            self.doctors_table.setItem(row_idx, 0, item_id)
            
            item_name = QTableWidgetItem(d["full_name"])
            item_name.setTextAlignment(int(Qt.AlignRight) | int(Qt.AlignVCenter))
            self.doctors_table.setItem(row_idx, 1, item_name)

        self._sources = catalog_service.get_referral_sources()
        self.sources_table.setRowCount(0)
        for row_idx, s in enumerate(self._sources):
            self.sources_table.insertRow(row_idx)
            
            item_id = QTableWidgetItem(str(s["id"]))
            item_id.setTextAlignment(int(Qt.AlignCenter))
            self.sources_table.setItem(row_idx, 0, item_id)
            
            item_name = QTableWidgetItem(s["name"])
            item_name.setTextAlignment(int(Qt.AlignRight) | int(Qt.AlignVCenter))
            self.sources_table.setItem(row_idx, 1, item_name)

    def add_doctor(self):
        name = self.new_doctor_edit.text().strip()
        if not name:
            return
        catalog_service.save_doctor(name)
        self.new_doctor_edit.clear()
        self.refresh_doctors_sources()

    def deactivate_selected_doctor(self):
        row = self.doctors_table.currentRow()
        if row < 0 or row >= len(self._doctors):
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
        row = self.sources_table.currentRow()
        if row < 0 or row >= len(self._sources):
            return
        catalog_service.deactivate_referral_source(self._sources[row]["id"])
        self.refresh_doctors_sources()
        self._reload_sources_combo()
