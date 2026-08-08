from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication
from app.ui.styles import apply_theme, get_saved_theme
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import (QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
                                 QLabel, QListWidget, QMessageBox, QPushButton, QScrollArea, QTableWidget,
                                 QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QStackedWidget)
from app.ui.animated_button import AnimatedButton

from app.config import get_logo_path
from app.services import catalog_service
from app.ui.attendance_view import AttendanceView
from app.ui.audit_log_view import AuditLogView
from app.ui.backup_view import BackupView
from app.ui.catalog_view import CatalogView
from app.ui.dashboard_view import DashboardView
from app.ui.patient_history_view import PatientHistoryView
from app.ui.patient_tracker_widget import PatientTrackerWidget
from app.ui.reception_view import ReceptionView
from app.ui.qc_view import QCView
from app.ui.reports_view import ReportsView
from app.ui.results_view import ResultsView
from app.ui.specimen_tracking_view import SpecimenTrackingView

from app.ui.pdf_designer_view import PdfDesignerView
from app.ui.settings_view import SettingsView
from app.ui.users_view import UsersView
from app.ui.visits_view import VisitsView


class DynamicStackedWidget(QStackedWidget):
    """QStackedWidget that calculates sizeHint based ONLY on the currently active page.
    This prevents short pages (e.g. UsersView) from displaying unnecessary scrollbars.
    """
    def sizeHint(self):
        curr = self.currentWidget()
        if curr:
            return curr.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        curr = self.currentWidget()
        if curr:
            return curr.minimumSizeHint()
        return super().minimumSizeHint()


class MainWindow(QWidget):
    def __init__(self, user, on_logout):
        super().__init__()
        self.user = user
        self.on_logout = on_logout
        self._closing_for_logout = False
        settings = catalog_service.get_lab_settings()
        app_title = settings.get("app_title") or settings.get("lab_name") or "LapLIS"
        self.setWindowTitle(app_title)


        logo_path = get_logo_path()

        if logo_path:
            self.setWindowIcon(QIcon(logo_path))

        # Fallback size and minimum size optimized for small/medium laptop screens (down to 980x580)
        self.resize(1280, 768)
        self.setMinimumSize(980, 580)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(190)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        if logo_path:
            logo_label = QLabel()
            pixmap = QPixmap(logo_path).scaledToWidth(65, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("padding-top: 16px; padding-bottom: 4px;")
            sidebar_layout.addWidget(logo_label)

        settings = catalog_service.get_lab_settings()
        name_label = QLabel(settings.get("lab_name") or "المعمل")
        name_label.setObjectName("SidebarTitle")
        name_label.setWordWrap(True)
        sidebar_layout.addWidget(name_label)
        if settings.get("tagline"):
            tagline_label = QLabel(settings["tagline"])
            tagline_label.setObjectName("SidebarTagline")
            tagline_label.setWordWrap(True)
            sidebar_layout.addWidget(tagline_label)

        self.nav_buttons = {}
        self.pages = {}
        self.stack = DynamicStackedWidget()

        # Grouped with section headers so the sidebar reads as "daily work" vs. "administration"
        # instead of one flat list of unrelated screen names.
        nav_groups = [
            (None, [
                ("Dashboard", "لوحة المتابعة", DashboardView),
            ]),
            ("العمليات اليومية", [
                ("Reception", "استقبال", ReceptionView),
                ("Visits", "الزيارات والفواتير", VisitsView),
                ("Results", "نتائج التحاليل", ResultsView),
                ("PatientHistory", "سجل المريض", PatientHistoryView),
                ("PatientTracker", "تتبّع المريض", PatientTrackerWidget),
                ("SpecimenTracking", "متابعة العينات", SpecimenTrackingView),
                ("Attendance", "الحضور والانصراف", AttendanceView),
            ]),
            ("الإدارة", [
                ("Catalog", "كتالوج التحاليل", CatalogView),
                ("QualityControl", "مراقبة الجودة (QC)", QCView),
                ("Reports", "التقارير والإحصائيات", ReportsView),
                ("PdfDesigner", "تصميم الـ PDF والطباعة", PdfDesignerView),
                ("Settings", "الإعدادات", SettingsView),
                ("Users", "المستخدمون والأدوار", UsersView),
                ("Audit", "سجل التدقيق", AuditLogView),
                ("Backup", "النسخ الاحتياطي والاستعادة", BackupView),
            ]),

        ]

        for section_title, items in nav_groups:
            visible_items = [i for i in items if user.can_view(i[0])]
            if not visible_items:
                continue
            if section_title:
                section_label = QLabel(section_title)
                section_label.setObjectName("SidebarSection")
                sidebar_layout.addWidget(section_label)
            for module_key, label, view_cls in visible_items:
                button = AnimatedButton(label)
                button.setObjectName("NavButton")
                button.clicked.connect(lambda checked=False, k=module_key: self.navigate(k))
                sidebar_layout.addWidget(button)
                self.nav_buttons[module_key] = button
                self.pages[module_key] = view_cls

        sidebar_layout.addStretch()

        user_label = QLabel(user.full_name)
        user_label.setObjectName("SidebarUser")
        sidebar_layout.addWidget(user_label)
        role_label = QLabel(user.role_name)
        role_label.setObjectName("SidebarRole")
        sidebar_layout.addWidget(role_label)

        from app.ui.styles import apply_theme, get_saved_theme
        current_theme = get_saved_theme()
        theme_label = "🌙 الوضع المظلم" if current_theme == "light" else "☀️ الوضع الفاتح"
        self.theme_button = AnimatedButton(theme_label)
        self.theme_button.setObjectName("NavButton")
        self.theme_button.setToolTip("التبديل بين الوضع الفاتح والوضع المظلم")
        self.theme_button.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_button)

        logout_button = AnimatedButton("تسجيل الخروج")
        logout_button.setObjectName("NavButton")
        logout_button.setToolTip("إنهاء الجلسة الحالية والعودة لشاشة تسجيل الدخول")
        logout_button.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_button)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setObjectName("SidebarScroll")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QScrollArea.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setFixedWidth(190)
        sidebar_scroll.setWidget(sidebar)

        root.addWidget(sidebar_scroll)
        # Apply saved theme on startup
        apply_theme(QApplication.instance(), get_saved_theme())

        root.addWidget(self.stack, 1)

        self._loaded_views = {}
        if self.nav_buttons:
            first_key = next(iter(self.nav_buttons))
            self.navigate(first_key)

    def navigate(self, module_key):
        if module_key not in self._loaded_views:
            view_cls = self.pages[module_key]
            try:
                # try passing current user to the view if it accepts it
                view = view_cls(self.user)
            except TypeError:
                view = view_cls()
            self._loaded_views[module_key] = view
            self.stack.addWidget(view)
        else:
            view = self._loaded_views[module_key]
            if hasattr(view, "refresh"):
                view.refresh()

        self.stack.setCurrentWidget(view)
        self.stack.updateGeometry()

        for key, button in self.nav_buttons.items():
            button.setObjectName("NavButtonActive" if key == module_key else "NavButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def toggle_theme(self):
        from PySide2.QtWidgets import QApplication
        from app.ui.styles import apply_theme, get_saved_theme
        new_theme = "dark" if get_saved_theme() == "light" else "light"
        apply_theme(QApplication.instance(), new_theme)
        self.theme_button.setText("🌙 الوضع المظلم" if new_theme == "light" else "☀️ الوضع الفاتح")

    def logout(self):
        # Logout closes this window to swap back to the login screen - it must not quit the whole
        # application the way closing the window via the OS titlebar (a real exit) should.
        self._closing_for_logout = True
        self.on_logout()

    def closeEvent(self, event):
        """Ensure all background threads are asked to stop before the window closes.
        This prevents the "QThread: Destroyed while thread is still running" warning.
        """
        try:
            # Import the global thread registry from worker module
            from app.utils.worker import _ACTIVE_THREADS
            for thread in list(_ACTIVE_THREADS):
                # Ask each thread to stop and wait for it to finish
                if hasattr(thread, "request_stop"):
                    thread.request_stop()
                thread.wait(3000)  # wait up to 3 seconds per thread
        except Exception:
            pass
        event.accept()
        if not self._closing_for_logout:
            self._quit_app()

    def _quit_app(self):
        # Kept as a thin, patchable indirection: PySide2/Shiboken's QApplication.quit is a C++
        # bound method that isn't reliably interceptable via monkeypatch.setattr from tests.
        QApplication.quit()
