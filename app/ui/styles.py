"""Shared QSS stylesheet: same brand palette as the .NET edition (#0B4F6C dark teal / #146C8E teal).

Sized and spaced generously on purpose - this app is used by non-technical lab/reception staff,
often on ordinary office monitors, so bigger touch/click targets and clearer text beat a dense,
"more fits on screen" layout every time.
"""

STYLESHEET = """
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

/* ---- Guidance banner: one friendly line at the top of a screen explaining what it's for ---- */
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
    selection-background-color: #146C8E;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QDateEdit:focus {
    border: 1.5px solid #146C8E;
}
QListWidget, QTreeWidget {
    background: white;
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
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    gridline-color: #F0F1F3;
}
QHeaderView::section {
    background-color: #146C8E;
    color: white;
    padding: 7px;
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
    font-weight: bold;
}
"""
