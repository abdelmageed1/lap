from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import (QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget)

from app.config import get_logo_path
from app.services import auth_service, catalog_service


class LoginWindow(QWidget):
    logged_in = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("تسجيل الدخول")
        self.resize(420, 520)

        logo_path = get_logo_path()
        if logo_path:
            self.setWindowIcon(QIcon(logo_path))

        settings = catalog_service.get_lab_settings()

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(340)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(28, 28, 28, 28)

        if logo_path:
            logo_label = QLabel()
            pixmap = QPixmap(logo_path).scaledToWidth(90, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(logo_label)

        title = QLabel(settings.get("lab_name") or "المعمل")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0B4F6C;")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        if settings.get("tagline"):
            tagline = QLabel(settings["tagline"])
            tagline.setStyleSheet("color: #6B7280; font-size: 11px;")
            tagline.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(tagline)

        card_layout.addSpacing(16)

        card_layout.addWidget(QLabel("اسم المستخدم"))
        self.username_edit = QLineEdit()
        self.username_edit.returnPressed.connect(self.password_edit_focus_or_login)
        card_layout.addWidget(self.username_edit)

        card_layout.addWidget(QLabel("كلمة المرور"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.returnPressed.connect(self.try_login)
        card_layout.addWidget(self.password_edit)

        card_layout.addSpacing(8)
        login_button = QPushButton("دخول")
        login_button.setObjectName("Primary")
        login_button.setToolTip("أو اضغط Enter في حقل كلمة المرور")
        login_button.clicked.connect(self.try_login)
        card_layout.addWidget(login_button)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #C62828;")
        self.error_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.error_label)

        hint = QLabel("بيانات الدخول الافتراضية: admin / Admin@123")
        hint.setStyleSheet("color: #9CA3AF; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(hint)

        outer.addWidget(card)

    def password_edit_focus_or_login(self):
        self.password_edit.setFocus()

    def try_login(self):
        user = auth_service.login(self.username_edit.text().strip(), self.password_edit.text())
        if user is None:
            self.error_label.setText("اسم المستخدم أو كلمة المرور غير صحيحة")
            return
        self.logged_in.emit(user)
