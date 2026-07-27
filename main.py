"""Entry point for the Windows-7-compatible (Python + PySide2) edition of LapLIS."""
import sys

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication

from app.db import init_schema
from app.seed import seed_if_empty
from app.ui.styles import STYLESHEET


def main():
    init_schema()
    seed_if_empty()

    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setStyleSheet(STYLESHEET)

    state = {"main_window": None, "login_window": None}

    def show_login():
        from app.ui.login_window import LoginWindow
        login = LoginWindow()
        login.logged_in.connect(on_logged_in)
        state["login_window"] = login
        login.show()

    def on_logged_in(user):
        from app.ui.main_window import MainWindow
        state["login_window"].close()
        window = MainWindow(user, on_logout=show_login_after_logout)
        state["main_window"] = window
        window.showMaximized()

    def show_login_after_logout():
        state["main_window"].close()
        show_login()

    show_login()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
