"""Centralized Light & Dark mode Theme System with color variables (tokens)."""

from PySide2.QtCore import QSettings
from PySide2.QtWidgets import QApplication

# Semantic Theme Color Variables (Tokens) for Light and Dark modes
THEME_TOKENS = {
    "light": {
        "primary": "#0B4F6C",
        "primary_hover": "#146C8E",
        "primary_text": "#0B4F6C",
        "bg_app": "#F4F7F9",
        "bg_card": "#FFFFFF",
        "bg_subtle": "#F8FAFC",
        "border": "#E5E7EB",
        "border_light": "#CBD5E1",
        "text_main": "#1F2937",
        "text_muted": "#64748B",
        "text_emphasis": "#0F172A",
        "sidebar_bg": "#0B4F6C",
        "sidebar_hover": "#146C8E",
        "sidebar_text": "#E2E8F0",
        "sidebar_title": "#FFFFFF",
        "sidebar_muted": "#94A3B8",
        "sidebar_section": "#38BDF8",
        "accent": "#0369A1",
        "accent_bg": "#E0F2FE",
        "danger": "#C62828",
        "danger_hover": "#9E1F1F",
        "danger_bg": "#FEF2F2",
        "success": "#166534",
        "success_bg": "#DCFCE7",
        "warning": "#D97706",
        "warning_bg": "#FEF3C7",
    },
    "dark": {
        "primary": "#38BDF8",
        "primary_hover": "#0284C7",
        "primary_text": "#38BDF8",
        "bg_app": "#0F172A",
        "bg_card": "#1E293B",
        "bg_subtle": "#334155",
        "border": "#334155",
        "border_light": "#475569",
        "text_main": "#F8FAFC",
        "text_muted": "#94A3B8",
        "text_emphasis": "#F1F5F9",
        "sidebar_bg": "#1E293B",
        "sidebar_hover": "#334155",
        "sidebar_text": "#CBD5E1",
        "sidebar_title": "#38BDF8",
        "sidebar_muted": "#94A3B8",
        "sidebar_section": "#38BDF8",
        "accent": "#38BDF8",
        "accent_bg": "#075985",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "danger_bg": "#450A0A",
        "success": "#4ADE80",
        "success_bg": "#052E16",
        "warning": "#FBBF24",
        "warning_bg": "#451A03",
    }
}

_current_theme = "light"
_theme_listeners = []


def get_saved_theme() -> str:
    settings = QSettings("LapLIS", "Preferences")
    return settings.value("theme", "light")


def set_saved_theme(theme_name: str):
    global _current_theme
    _current_theme = theme_name
    settings = QSettings("LapLIS", "Preferences")
    settings.setValue("theme", theme_name)


def get_current_theme() -> str:
    global _current_theme
    return _current_theme


def get_theme_tokens(theme_name: str = None) -> dict:
    t = theme_name or get_current_theme()
    return THEME_TOKENS.get(t, THEME_TOKENS["light"])


def get_color(token_name: str) -> str:
    tokens = get_theme_tokens()
    return tokens.get(token_name, "#000000")


def register_theme_listener(callback_fn):
    if callback_fn not in _theme_listeners:
        _theme_listeners.append(callback_fn)


def unregister_theme_listener(callback_fn):
    if callback_fn in _theme_listeners:
        _theme_listeners.remove(callback_fn)


def generate_stylesheet(theme_name: str) -> str:
    c = get_theme_tokens(theme_name)
    return f"""
QWidget {{
    font-family: "Tahoma", "DejaVu Sans", sans-serif;
    font-size: 13px;
    color: {c['text_main']};
}}
QMainWindow, QDialog {{
    background-color: {c['bg_app']};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
#SidebarScroll, #Sidebar {{
    background-color: {c['sidebar_bg']};
}}
#SidebarTitle {{
    color: {c['sidebar_title']};
    font-size: 15px;
    font-weight: bold;
    padding: 12px 10px 3px 10px;
}}
#SidebarTagline {{
    color: {c['sidebar_muted']};
    font-size: 10.5px;
    padding: 0 10px 12px 10px;
}}
#SidebarSection {{
    color: {c['sidebar_section']};
    font-size: 10.5px;
    font-weight: bold;
    padding: 10px 12px 4px 12px;
}}
#SidebarUser {{
    color: {c['sidebar_title']};
    padding: 6px 12px;
    font-weight: bold;
    font-size: 12.5px;
}}
#SidebarRole {{
    color: {c['sidebar_muted']};
    padding: 0 12px 6px 12px;
    font-size: 10px;
}}
QPushButton#NavButton {{
    background-color: transparent;
    color: {c['sidebar_text']};
    text-align: right;
    padding: 9px 12px;
    border: none;
    font-size: 13px;
}}
QPushButton#NavButton:hover {{
    background-color: {c['sidebar_hover']};
    color: #FFFFFF;
}}
QPushButton#NavButtonActive {{
    background-color: {c['sidebar_hover']};
    color: #FFFFFF;
    text-align: right;
    padding: 9px 12px;
    border-right: 4px solid {c['sidebar_section']};
    font-weight: bold;
    font-size: 13px;
}}
QLabel#PageTitle {{
    font-size: 18px;
    font-weight: bold;
    color: {c['primary_text']};
    padding: 2px 0 2px 0;
}}

QFrame#HintBanner {{
    background-color: {c['bg_subtle']};
    border: 1px solid {c['border']};
    border-radius: 6px;
}}
QLabel#HintIcon {{
    color: {c['primary']};
    font-size: 14px;
    font-weight: bold;
}}
QLabel#HintText {{
    color: {c['text_main']};
    font-size: 12px;
}}
QLabel#StepLabel {{
    color: {c['primary']};
    font-weight: bold;
    font-size: 14px;
    padding: 2px 0 4px 0;
}}

QFrame#Card {{
    background-color: {c['bg_card']};
    border-radius: 8px;
    border: 1px solid {c['border']};
}}
QLabel#SummaryValueLabel {{
    font-size: 20px;
    font-weight: 700;
    color: {c['primary_text']};
}}
QPushButton#Primary {{
    background-color: {c['primary'] if theme_name == 'light' else c['primary_hover']};
    color: white;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: bold;
    border: none;
    font-size: 13px;
}}
QPushButton#Primary:hover {{
    background-color: {c['primary_hover'] if theme_name == 'light' else c['primary']};
}}
QPushButton#Secondary {{
    background-color: {c['bg_card'] if theme_name == 'light' else c['bg_subtle']};
    color: {c['text_main']};
    border: 1px solid {c['border_light']};
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton#Secondary:hover {{
    background-color: {c['bg_subtle'] if theme_name == 'light' else c['border_light']};
    border-color: {c['primary']};
    color: {c['text_emphasis']};
}}
QPushButton#Danger {{
    background-color: {c['danger']};
    color: white;
    border-radius: 5px;
    padding: 6px 14px;
    font-weight: bold;
    border: none;
    font-size: 13px;
}}
QPushButton#Danger:hover {{
    background-color: {c['danger_hover']};
}}
QPushButton {{
    background-color: {c['bg_card'] if theme_name == 'light' else c['bg_subtle']};
    color: {c['text_main']};
    border: 1px solid {c['border_light']};
    border-radius: 5px;
    padding: 6px 14px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {c['bg_subtle'] if theme_name == 'light' else c['border_light']};
    border-color: {c['primary']};
}}
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {{
    padding: 5px 8px;
    border: 1px solid {c['border_light']};
    border-radius: 5px;
    background: {c['bg_card'] if theme_name == 'light' else c['bg_subtle']};
    color: {c['text_main']};
    selection-background-color: {c['primary']};
    font-size: 13px;
}}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus {{
    border: 1.5px solid {c['primary']};
}}
QListWidget, QTreeWidget {{
    background: {c['bg_card'] if theme_name == 'light' else c['bg_subtle']};
    color: {c['text_main']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item, QTreeWidget::item {{
    padding: 4px 4px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {c['primary']};
    color: white;
}}
QTableWidget {{
    background: {c['bg_card'] if theme_name == 'light' else c['bg_subtle']};
    color: {c['text_main']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    gridline-color: {c['border']};
    selection-background-color: {c['accent_bg']};
    selection-color: {c['primary_text']};
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 4px 5px;
}}
QHeaderView::section {{
    background-color: {c['primary'] if theme_name == 'light' else c['primary_hover']};
    color: white;
    padding: 5px 7px;
    border: none;
    font-weight: bold;
    font-size: 13px;
}}
QTabWidget::pane {{
    border: 1px solid {c['border']};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: {c['bg_subtle']};
    color: {c['text_muted']};
    padding: 5px 10px;
    font-size: 13px;
    border: 1px solid {c['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: {c['bg_card']};
    color: {c['primary_text']};
    font-weight: bold;
}}
QScrollBar:vertical {{
    border: none;
    background: {c['bg_subtle']};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {c['border_light']};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c['primary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    border: none;
    background: {c['bg_subtle']};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {c['border_light']};
    min-width: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c['primary']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


LIGHT_STYLESHEET = generate_stylesheet("light")
DARK_STYLESHEET = generate_stylesheet("dark")
STYLESHEET = LIGHT_STYLESHEET


def apply_theme(app, theme_name: str):
    set_saved_theme(theme_name)
    stylesheet = generate_stylesheet(theme_name)
    if app is None:
        app = QApplication.instance()
    if app:
        app.setStyleSheet(stylesheet)
    
    # Notify listeners
    for callback in list(_theme_listeners):
        try:
            callback(theme_name)
        except Exception:
            pass


def toggle_theme(app=None) -> str:
    new_theme = "dark" if get_current_theme() == "light" else "light"
    apply_theme(app, new_theme)
    return new_theme
