import subprocess
import sys

from PySide2.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton,
                                QVBoxLayout, QWidget)

from app.config import BACKUPS_DIR
from app.services import backup_service
from app.ui.widgets import HintBanner, wrappable_path
from app.utils.audit import log_action


class BackupView(QWidget):
    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()
        outer = QVBoxLayout(self)
        title = QLabel("النسخ الاحتياطي والاستعادة")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "النسخة الاحتياطية تحتوي على كل بيانات النظام معًا (المرضى، الزيارات، النتائج، وكتالوج "
            f"التحاليل والأسعار) في ملف واحد، وتُحفظ دائمًا في مسار واضح وسهل الوصول إليه:\n{wrappable_path(BACKUPS_DIR)}"
        ))

        actions_row = QHBoxLayout()
        create_button = QPushButton("إنشاء نسخة احتياطية الآن")
        create_button.setObjectName("Primary")
        create_button.setToolTip("يُنصَح بعمل نسخة احتياطية يوميًا أو قبل أي تحديث للبرنامج")
        create_button.clicked.connect(self.create_backup_now)
        actions_row.addWidget(create_button)
        open_folder_button = QPushButton("فتح مجلد النسخ الاحتياطية")
        open_folder_button.setToolTip("يفتح مجلد النسخ الاحتياطية في مستكشف الملفات لنسخها لمكان آمن (فلاشة مثلًا)")
        open_folder_button.clicked.connect(self.open_backups_folder)
        actions_row.addWidget(open_folder_button)
        outer.addLayout(actions_row)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        outer.addWidget(self.message_label)

        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.addWidget(self._label_bold("النسخ الاحتياطية المتوفرة"))
        self.backups_list = QListWidget()
        self.backups_list.setToolTip("اختر نسخة من القائمة ثم اضغط 'استعادة النسخة المحددة' أدناه")
        list_layout.addWidget(self.backups_list)
        restore_button = QPushButton("استعادة النسخة المحددة")
        restore_button.setToolTip("يستبدل بيانات النظام الحالية بهذه النسخة (بعد تأكيد وأخذ نسخة أمان تلقائيًا)")
        restore_button.clicked.connect(self.restore_selected)
        list_layout.addWidget(restore_button)
        outer.addWidget(list_card)

        self.backups = []
        self.refresh()

    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-weight: bold; color: #0B4F6C;")
        return label

    def _open_path(self, path):
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

    def refresh(self):
        self.backups = backup_service.list_backups()
        self.backups_list.clear()
        for b in self.backups:
            self.backups_list.addItem(b["name"])

    def create_backup_now(self):
        path = backup_service.create_backup()
        self.message_label.setText(f"تم إنشاء نسخة احتياطية بنجاح في:\n{wrappable_path(path)}")
        self.message_label.setStyleSheet("color: #146C8E;")
        try:
            if self.current_user:
                log_action('database', None, 'backup_create', user_id=self.current_user.user_id, details=path)
        except Exception:
            pass
        self.refresh()

    def open_backups_folder(self):
        self._open_path(BACKUPS_DIR)

    def restore_selected(self):
        row = self.backups_list.currentRow()
        if row < 0:
            self.message_label.setText("اختر نسخة احتياطية من القائمة أولًا")
            self.message_label.setStyleSheet("color: #C62828;")
            return
        backup = self.backups[row]
        # Built manually with addButton()/YesRole rather than QMessageBox.warning(..., Yes|No, No):
        # OR-ing QMessageBox.StandardButton flags together raises a TypeError on this PySide2/Python
        # build ("StandardButton object cannot be interpreted as an integer") - addButton() sidesteps
        # the flag-enum entirely.
        box = QMessageBox(self)
        box.setWindowTitle("تأكيد الاستعادة")
        box.setIcon(QMessageBox.Warning)
        box.setText(
            "سيتم استبدال كل بيانات النظام الحالية بمحتوى هذه النسخة الاحتياطية:\n"
            f"{backup['name']}\n\n"
            "سيتم أخذ نسخة أمان من البيانات الحالية تلقائيًا قبل الاستبدال.\n"
            "يجب إغلاق التطبيق وإعادة تشغيله بعد الاستعادة لرؤية البيانات المستعادة بشكل صحيح.\n\n"
            "هل أنت متأكد من المتابعة؟"
        )
        yes_button = box.addButton("نعم، استعادة", QMessageBox.YesRole)
        cancel_button = box.addButton("إلغاء", QMessageBox.NoRole)
        box.setDefaultButton(cancel_button)
        box.exec_()
        if box.clickedButton() is not yes_button:
            return
        pre_restore_path = backup_service.restore_backup(backup["path"])
        try:
            if self.current_user:
                log_action('database', None, 'backup_restore', user_id=self.current_user.user_id,
                            details=f"restored={backup['path']} safety_copy={pre_restore_path}")
        except Exception:
            pass
        self.message_label.setText(
            f"تمت الاستعادة بنجاح. تم حفظ نسخة أمان من البيانات السابقة في:\n{wrappable_path(pre_restore_path)}\n\n"
            "أغلق التطبيق الآن وأعد تشغيله."
        )
        self.message_label.setStyleSheet("color: #146C8E;")
        self.refresh()
