"""Regression test: logging out must return to the login screen, not quit the whole application.

MainWindow.closeEvent() used to call QApplication.quit() unconditionally - which fires even when
the window is closed programmatically as part of logout (main.py's show_login_after_logout()
calls main_window.close()), so clicking "logout" closed the entire app instead of showing the
login screen again."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide2.QtWidgets import QApplication

from app.services import auth_service
from app.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


def _fake_user():
    return auth_service.CurrentUser(1, "admin", "Admin", 1, "مدير النظام")


def test_logout_does_not_call_application_quit(monkeypatch):
    logout_calls = []
    mw = MainWindow(_fake_user(), on_logout=lambda: logout_calls.append(1))
    quit_calls = []
    monkeypatch.setattr(mw, "_quit_app", lambda: quit_calls.append(1))
    mw.show()
    _app.processEvents()

    mw.logout()

    assert logout_calls == [1], "on_logout callback must fire so the login screen can be shown"
    assert quit_calls == [], "logout must not quit the whole application"


def test_closing_the_window_directly_still_quits_the_application(monkeypatch):
    """The OS titlebar close (X) button - i.e. closing the window without going through the
    logout button - is a real exit and must still shut the application down."""
    mw = MainWindow(_fake_user(), on_logout=lambda: None)
    quit_calls = []
    monkeypatch.setattr(mw, "_quit_app", lambda: quit_calls.append(1))
    mw.show()
    _app.processEvents()

    mw.close()

    assert quit_calls == [1]
