"""Shared QSS stylesheet with Light & Dark mode support."""

from PySide2.QtCore import QSettings

LIGHT_STYLESHEET = """
QWidget {
    font-family: "Tahoma", "DejaVu Sans", sans-serif;
    font-size: 14px;
    color: #1F2937;
}
QMainWindow, QDialog {
    background-color: #F4F7F9;
}
QScrollArea {
    border: none;
    background: transparent;
}
#Sidebar {
    background-color: #0B4F6C;
}
#SidebarTitle {
    color: white;
    font-size: 16px;
    font-weight: bold;
    padding: 18px 14px 4px 14px;
}
#SidebarTagline {
    color: #CBD5E1;
    font-size: 11px;
    padding: 0 14px 18px 14px;
}
#SidebarSection {
    color: #7FA8BC;
    font-size: 11px;
    font-weight: bold;
    padding: 16px 16px 6px 16px;
}
QPushButton#NavButton {
    background-color: transparent;
    color: #E2E8F0;
    text-align: right;
    padding: 13px 16px;
    border: none;
    font-size: 14px;
}
QPushButton#NavButton:hover {
    background-color: #146C8E;
}
QPushButton#NavButtonActive {
    background-color: #146C8E;
    color: white;
    text-align: right;
    padding: 13px 16px;
    border-right: 4px solid white;
    font-weight: bold;
    font-size: 14px;
}
QLabel#PageTitle {
    font-size: 21px;
    font-weight: bold;
    color: #0B4F6C;
    padding: 4px 0 4px 0;
}

QFrame#HintBanner {
    background-color: #EAF4F8;
    border: 1px solid #BFE0EA;
    border-radius: 6px;
}
QLabel#HintIcon {
    color: #146C8E;
    font-size: 15px;
    font-weight: bold;
}
QLabel#HintText {
    color: #0B4F6C;
    font-size: 12.5px;
}
QLabel#StepLabel {
    color: #146C8E;
    font-weight: bold;
    font-size: 14.5px;
    padding: 2px 0 6px 0;
}

QFrame#Card {
    background-color: white;
    border-radius: 10px;
    border: 1px solid #E5E7EB;
}
QLabel#SummaryValueLabel {
    font-size: 22px;
    font-weight: 700;
    color: #0B4F6C;
}
QPushButton#Primary {
    background-color: #146C8E;
    color: white;
    border-radius: 5px;
    padding: 9px 20px;
    font-weight: bold;
    border: none;
}
QPushButton#Primary:hover {
    background-color: #0B4F6C;
}
QPushButton#Danger {
    background-color: #C62828;
    color: white;
    border-radius: 5px;
    padding: 7px 16px;
    border: none;
}
QPushButton#Danger:hover {
    background-color: #9E1F1F;
}
QPushButton {
    background-color: #FFFFFF;
    color: #0B4F6C;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #EAF4F8;
    border-color: #146C8E;
}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {
    padding: 7px 9px;
    border: 1px solid #D1D5DB;
    border-radius: 5px;
    background: white;
    color: #1F2937;
    selection-background-color: #146C8E;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus {
    border: 1.5px solid #146C8E;
}
QListWidget, QTreeWidget {
    background: white;
    color: #1F2937;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    outline: none;
}
QListWidget::item, QTreeWidget::item {
    padding: 5px 4px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #146C8E;
    color: white;
}
QTableWidget {
    background: white;
    color: #1F2937;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    gridline-color: #F0F1F3;
    selection-background-color: #EAF4F8;
    selection-color: #0B4F6C;
}
QTableWidget::item {
    padding: 6px;
}
QHeaderView::section {
    background-color: #146C8E;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background: #EEF2F5;
    color: #0B4F6C;
    padding: 9px 18px;
    border: 1px solid #E5E7EB;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: white;
    color: #0B4F6C;
    font-weight: bold;
}
"""

DARK_STYLESHEET = """
QWidget {
    font-family: "Tahoma", "DejaVu Sans", sans-serif;
    font-size: 14px;
    color: #F8FAFC;
}
QMainWindow, QDialog {
    background-color: #0F172A;
}
QScrollArea {
    border: none;
    background: transparent;
}
#Sidebar {
    background-color: #1E293B;
}
#SidebarTitle {
    color: #38BDF8;
    font-size: 16px;
    font-weight: bold;
    padding: 18px 14px 4px 14px;
}
#SidebarTagline {
    color: #94A3B8;
    font-size: 11px;
    padding: 0 14px 18px 14px;
}
#SidebarSection {
    color: #38BDF8;
    font-size: 11px;
    font-weight: bold;
    padding: 16px 16px 6px 16px;
}
QPushButton#NavButton {
    background-color: transparent;
    color: #CBD5E1;
    text-align: right;
    padding: 13px 16px;
    border: none;
    font-size: 14px;
}
QPushButton#NavButton:hover {
    background-color: #334155;
    color: #F8FAFC;
}
QPushButton#NavButtonActive {
    background-color: #0284C7;
    color: white;
    text-align: right;
    padding: 13px 16px;
    border-right: 4px solid #38BDF8;
    font-weight: bold;
    font-size: 14px;
}
QLabel#PageTitle {
    font-size: 21px;
    font-weight: bold;
    color: #38BDF8;
    padding: 4px 0 4px 0;
}

QFrame#HintBanner {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
}
QLabel#HintIcon {
    color: #38BDF8;
    font-size: 15px;
    font-weight: bold;
}
QLabel#HintText {
    color: #CBD5E1;
    font-size: 12.5px;
}
QLabel#StepLabel {
    color: #38BDF8;
    font-weight: bold;
    font-size: 14.5px;
    padding: 2px 0 6px 0;
}

QFrame#Card {
    background-color: #1E293B;
    border-radius: 10px;
    border: 1px solid #334155;
}
QPushButton#Primary {
    background-color: #0284C7;
    color: white;
    border-radius: 5px;
    padding: 9px 20px;
    font-weight: bold;
    border: none;
}
QPushButton#Primary:hover {
    background-color: #0369A1;
}
QPushButton#Danger {
    background-color: #EF4444;
    color: white;
    border-radius: 5px;
    padding: 7px 16px;
    border: none;
}
QPushButton#Danger:hover {
    background-color: #DC2626;
}
QPushButton {
    background-color: #334155;
    color: #F8FAFC;
    border: 1px solid #475569;
    border-radius: 5px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #475569;
    border-color: #38BDF8;
}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {
    padding: 7px 9px;
    border: 1px solid #475569;
    border-radius: 5px;
    background: #1E293B;
    color: #F8FAFC;
    selection-background-color: #0284C7;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus {
    border: 1.5px solid #38BDF8;
}
QListWidget, QTreeWidget {
    background: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    outline: none;
}
QListWidget::item, QTreeWidget::item {
    padding: 5px 4px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #0284C7;
    color: white;
}
QTableWidget {
    background: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #334155;
}
QHeaderView::section {
    background-color: #0284C7;
    color: white;
    padding: 7px;
    border: none;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background: #1E293B;
    color: #CBD5E1;
    padding: 9px 18px;
    border: 1px solid #334155;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #334155;
    color: #F8FAFC;
    font-weight: bold;
}
"""

STYLESHEET = LIGHT_STYLESHEET


def get_saved_theme():
    settings = QSettings("LapLIS", "Preferences")
    return settings.value("theme", "light")


def set_saved_theme(theme_name):
    settings = QSettings("LapLIS", "Preferences")
    settings.setValue("theme", theme_name)


def apply_theme(app, theme_name):
    if theme_name == "dark":
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setStyleSheet(LIGHT_STYLESHEET)
    set_saved_theme(theme_name)
