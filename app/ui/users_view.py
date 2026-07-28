from PySide2.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
                                QLineEdit, QListWidget, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget)


from app.services import user_service
from app.ui.styles import get_color
from app.ui.widgets import HintBanner
from app.utils.audit import log_action


class UsersView(QWidget):
    def __init__(self, current_user=None):
        self.current_user = current_user
        super().__init__()
        outer = QVBoxLayout(self)
        title = QLabel("المستخدمون والأدوار")
        title.setObjectName("PageTitle")
        outer.addWidget(title)
        outer.addWidget(HintBanner(
            "من تبويب «المستخدمون» أضف حسابات جديدة أو عطِّل/فعِّل حسابًا أو غيِّر كلمة مروره. "
            "من تبويب «الأدوار والصلاحيات» حدِّد بالضبط ما يستطيع كل دور رؤيته وتعديله في كل شاشة."
        ))

        tabs = QTabWidget()
        outer.addWidget(tabs)
        tabs.addTab(self._build_users_tab(), "المستخدمون")
        tabs.addTab(self._build_roles_tab(), "الأدوار والصلاحيات")

    def _label_bold(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"font-weight: bold; color: {get_color('primary_text')};")
        return label

    # ---- Users tab ----
    def _build_users_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_layout = QVBoxLayout(form_card)
        form_layout.addWidget(self._label_bold("إضافة مستخدم جديد"))
        form_layout.addWidget(QLabel("اسم المستخدم"))
        self.username_edit = QLineEdit()
        form_layout.addWidget(self.username_edit)
        form_layout.addWidget(QLabel("الاسم بالكامل"))
        self.fullname_edit = QLineEdit()
        form_layout.addWidget(self.fullname_edit)
        form_layout.addWidget(QLabel("كلمة المرور"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_edit)
        form_layout.addWidget(QLabel("الدور"))
        self.role_combo = QComboBox()
        form_layout.addWidget(self.role_combo)
        add_button = QPushButton("إضافة")
        add_button.setObjectName("Primary")
        add_button.clicked.connect(self.add_user)
        form_layout.addWidget(add_button)
        self.user_message = QLabel("")
        form_layout.addWidget(self.user_message)
        form_layout.addStretch()
        layout.addWidget(form_card, 1)

        list_card = QFrame()
        list_card.setObjectName("Card")
        list_layout = QVBoxLayout(list_card)
        list_layout.addWidget(self._label_bold("المستخدمون المتاحون بالسيستم"))
        self.users_list = QListWidget()
        self.users_list.setMaximumHeight(160)
        self.users_list.setMinimumHeight(110)
        self.users_list.itemClicked.connect(self.on_select_user)
        list_layout.addWidget(self.users_list)

        # Edit Username Row (اسم الدخول)
        edit_username_row = QHBoxLayout()
        self.edit_username_edit = QLineEdit()
        self.edit_username_edit.setPlaceholderText("تعديل اسم الدخول (Username) للمستخدم المحدَّد...")
        btn_update_username = QPushButton("تغيير اسم الدخول 🔑")
        btn_update_username.setToolTip("تعديل اسم الدخول المستخدم لتسجيل الدخول للنظام (Username)")
        btn_update_username.clicked.connect(self.update_selected_username)
        edit_username_row.addWidget(self.edit_username_edit, 2)
        edit_username_row.addWidget(btn_update_username, 1)
        list_layout.addLayout(edit_username_row)

        # Edit Fullname Row
        edit_fullname_row = QHBoxLayout()
        self.edit_fullname_edit = QLineEdit()
        self.edit_fullname_edit.setPlaceholderText("تعديل الاسم بالكامل للمستخدم المحدَّد...")
        btn_update_fullname = QPushButton("تغيير الاسم بالكامل ✏️")
        btn_update_fullname.setToolTip("تعديل الاسم بالكامل المعروض للمستخدم في السجلات والطباعة")
        btn_update_fullname.clicked.connect(self.update_selected_user_fullname)
        edit_fullname_row.addWidget(self.edit_fullname_edit, 2)
        edit_fullname_row.addWidget(btn_update_fullname, 1)
        list_layout.addLayout(edit_fullname_row)

        selected_row = QHBoxLayout()
        self.toggle_active_button = QPushButton("تعطيل / تفعيل")
        self.toggle_active_button.setToolTip("اختر مستخدمًا من القائمة أعلاه أولًا، ثم اضغط هنا لتعطيله أو تفعيله")
        self.toggle_active_button.clicked.connect(self.toggle_selected_user_active)
        selected_row.addWidget(self.toggle_active_button)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setPlaceholderText("كلمة مرور جديدة")
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        selected_row.addWidget(self.new_password_edit)

        reset_button = QPushButton("إعادة تعيين كلمة المرور")
        reset_button.clicked.connect(self.reset_selected_user_password)
        selected_row.addWidget(reset_button)
        list_layout.addLayout(selected_row)

        # Delete User Row
        delete_row = QHBoxLayout()
        self.delete_user_button = QPushButton("حذف حساب المستخدم 🗑️")
        self.delete_user_button.setToolTip("حذف الحساب نهائيًا من السيستم (يتطلب موافقة وتأكيد كلمة سر الأدمن)")
        self.delete_user_button.setObjectName("Danger")
        self.delete_user_button.clicked.connect(self.delete_selected_user)
        delete_row.addWidget(self.delete_user_button)

        self.selected_user_message = QLabel("")
        delete_row.addWidget(self.selected_user_message, 1)
        list_layout.addLayout(delete_row)

        layout.addWidget(list_card, 1)

        self.users = []
        self.selected_user_id = None
        self.refresh_roles_combo()
        self.refresh_users()
        return widget

    def refresh_roles_combo(self):
        self.role_combo.clear()
        for r in user_service.get_roles():
            self.role_combo.addItem(r["name"], r["id"])

    def refresh_users(self):
        self.users = user_service.get_users()
        self.users_list.clear()
        for u in self.users:
            status = "مفعّل" if u["is_active"] else "معطّل"
            self.users_list.addItem(f"{u['username']} - {u['full_name']} - {u['role_name']} ({status})")

    def on_select_user(self, item):
        row = self.users_list.row(item)
        self.selected_user_id = self.users[row]["id"]
        selected_user = self.users[row]
        self.edit_username_edit.setText(selected_user["username"])
        self.edit_fullname_edit.setText(selected_user["full_name"])
        self.selected_user_message.setText(f"محدَّد: {selected_user['username']} ({selected_user['full_name']})")
        self.selected_user_message.setStyleSheet(f"color: {get_color('text_muted')};")

    def update_selected_username(self):
        if self.selected_user_id is None:
            self.selected_user_message.setText("اختر مستخدمًا أولًا")
            self.selected_user_message.setStyleSheet(f"color: {get_color('danger')};")
            return
        new_username = self.edit_username_edit.text().strip()
        if not new_username:
            self.selected_user_message.setText("أدخل اسم الدخول الجديد (Username)")
            self.selected_user_message.setStyleSheet(f"color: {get_color('danger')};")
            return

        from app.services import auth_service
        from app.ui.patient_history_view import AdminPasswordConfirmDialog
        dlg = AdminPasswordConfirmDialog(f"تأكيد تغيير اسم الدخول لـ {new_username}", self)
        if dlg.exec_() != dlg.Accepted:
            return
        curr_uid = getattr(self.current_user, "user_id", None) if self.current_user else None
        if not auth_service.verify_admin_password(dlg.get_password().strip(), user_id=curr_uid):
            QMessageBox.warning(self, "خطأ الأمان", "كلمة سر الأدمن غير صحيحة! تعذر تغيير اسم الدخول.")
            return

        ok, msg = user_service.update_username(self.selected_user_id, new_username)
        self.selected_user_message.setText(msg)
        self.selected_user_message.setStyleSheet(f"color: {get_color('primary')};" if ok else f"color: {get_color('danger')};")
        if ok:
            self.refresh_users()


    def update_selected_user_fullname(self):
        if self.selected_user_id is None:
            self.selected_user_message.setText("اختر مستخدمًا أولًا")
            self.selected_user_message.setStyleSheet(f"color: {get_color('danger')};")
            return
        new_name = self.edit_fullname_edit.text().strip()
        if not new_name:
            self.selected_user_message.setText("أدخل الاسم بالكامل الجديد")
            self.selected_user_message.setStyleSheet(f"color: {get_color('danger')};")
            return

        ok, msg = user_service.update_user_full_name(self.selected_user_id, new_name)
        self.selected_user_message.setText(msg)
        self.selected_user_message.setStyleSheet(f"color: {get_color('primary')};" if ok else f"color: {get_color('danger')};")
        if ok:
            self.refresh_users()

    def delete_selected_user(self):
        if self.selected_user_id is None:
            self.selected_user_message.setText("اختر مستخدمًا أولًا")
            self.selected_user_message.setStyleSheet(f"color: {get_color('danger')};")
            return
        current = next((u for u in self.users if u["id"] == self.selected_user_id), None)
        if not current:
            return

        if current["username"].lower() == "admin":
            QMessageBox.warning(self, "تنبيه الأمان", "لا يمكن حذف حساب المسؤول الرئيسي (admin).")
            return

        curr_uid = getattr(self.current_user, "user_id", None) if self.current_user else None
        if curr_uid and self.selected_user_id == curr_uid:
            QMessageBox.warning(self, "تنبيه الأمان", "لا يمكن حذف الحساب الذي تستخدمه حالياً للنظام.")
            return

        confirm = QMessageBox.question(
            self, "تأكيد حذف المستخدم",
            f"هل أنت تأكد من رغبتك في حذف حساب المستخدم النهائي ({current['full_name']} - {current['username']})؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        from app.services import auth_service
        from app.ui.patient_history_view import AdminPasswordConfirmDialog
        dlg = AdminPasswordConfirmDialog(f"تأكيد كلمة سر الأدمن لحذف حساب {current['username']}", self)
        if dlg.exec_() != dlg.Accepted:
            return
        if not auth_service.verify_admin_password(dlg.get_password().strip(), user_id=curr_uid):
            QMessageBox.warning(self, "خطأ الأمان", "كلمة سر الأدمن غير صحيحة! تعذر إتمام الحذف.")
            return

        ok, msg = user_service.delete_user(self.selected_user_id, current_user_id=curr_uid)
        if ok:
            QMessageBox.information(self, "تم الحذف", msg)
            self.selected_user_id = None
            self.edit_fullname_edit.clear()
            self.refresh_users()
        else:
            QMessageBox.warning(self, "خطأ الحذف", msg)


    def toggle_selected_user_active(self):
        if self.selected_user_id is None:
            self.selected_user_message.setText("اختر مستخدمًا أولًا")
            self.selected_user_message.setStyleSheet("color: #C62828;")
            return
        current = next((u for u in self.users if u["id"] == self.selected_user_id), None)
        if current is None:
            return
        if current["username"] == "admin" and current["is_active"]:
            self.selected_user_message.setText("لا يمكن تعطيل حساب admin")
            self.selected_user_message.setStyleSheet("color: #C62828;")
            return

        from app.services import auth_service
        from app.ui.patient_history_view import AdminPasswordConfirmDialog
        dlg = AdminPasswordConfirmDialog(f"تعديل حالة حساب {current['username']}", self)
        if dlg.exec_() != dlg.Accepted:
            return
        user_id = getattr(self.current_user, "user_id", None) if self.current_user else None
        if not auth_service.verify_admin_password(dlg.get_password().strip(), user_id=user_id):
            QMessageBox.warning(self, "خطأ الأمان", "كلمة سر الأدمن غير صحيحة! تعذر إتمام التغيير.")
            return

        new_active = not current["is_active"]
        user_service.set_user_active(self.selected_user_id, new_active)
        self.refresh_users()
        self.selected_user_message.setText("تم التحديث")
        self.selected_user_message.setStyleSheet("color: #146C8E;")
        try:
            if self.current_user:
                log_action('users', self.selected_user_id, 'ui_toggle_active', user_id=self.current_user.user_id,
                           details=f'is_active={new_active}')
        except Exception:
            pass

    def reset_selected_user_password(self):
        if self.selected_user_id is None:
            self.selected_user_message.setText("اختر مستخدمًا أولًا")
            self.selected_user_message.setStyleSheet("color: #C62828;")
            return
        new_password = self.new_password_edit.text()
        if not new_password:
            self.selected_user_message.setText("أدخل كلمة المرور الجديدة")
            self.selected_user_message.setStyleSheet("color: #C62828;")
            return

        from app.services import auth_service
        from app.ui.patient_history_view import AdminPasswordConfirmDialog
        dlg = AdminPasswordConfirmDialog("إعادة تعيين كلمة المرور للمستخدم", self)
        if dlg.exec_() != dlg.Accepted:
            return
        user_id = getattr(self.current_user, "user_id", None) if self.current_user else None
        if not auth_service.verify_admin_password(dlg.get_password().strip(), user_id=user_id):
            QMessageBox.warning(self, "خطأ الأمان", "كلمة سر الأدمن غير صحيحة! تعذر تعيين كلمة المرور.")
            return

        user_service.reset_password(self.selected_user_id, new_password)
        self.new_password_edit.clear()
        self.selected_user_message.setText("تم تغيير كلمة المرور بنجاح")
        self.selected_user_message.setStyleSheet("color: #146C8E;")
        try:
            if self.current_user:
                log_action('users', self.selected_user_id, 'ui_reset_password', user_id=self.current_user.user_id)
        except Exception:
            pass


    def add_user(self):
        username = self.username_edit.text().strip()
        ok, message = user_service.create_user(
            username, self.fullname_edit.text().strip(),
            self.password_edit.text(), self.role_combo.currentData(),
        )
        self.user_message.setText(message)
        self.user_message.setStyleSheet("color: #146C8E;" if ok else "color: #C62828;")
        if ok:
            self.username_edit.clear()
            self.fullname_edit.clear()
            self.password_edit.clear()
            self.refresh_users()
            try:
                if self.current_user:
                    log_action('users', None, 'ui_create_user', user_id=self.current_user.user_id,
                               details=f'username={username}')
            except Exception:
                pass

    # ---- Roles tab ----
    def _build_roles_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        roles_card = QFrame()
        roles_card.setObjectName("Card")
        roles_layout = QVBoxLayout(roles_card)
        add_row = QHBoxLayout()
        self.new_role_edit = QLineEdit()
        self.new_role_edit.setPlaceholderText("اسم الدور الجديد")
        add_role_button = QPushButton("إضافة")
        add_role_button.setObjectName("Primary")
        add_role_button.clicked.connect(self.add_role)
        add_row.addWidget(self.new_role_edit)
        add_row.addWidget(add_role_button)
        roles_layout.addLayout(add_row)

        self.roles_list = QListWidget()
        self.roles_list.setMaximumHeight(200)
        self.roles_list.itemClicked.connect(self.show_permissions)
        roles_layout.addWidget(self.roles_list)
        layout.addWidget(roles_card, 1)

        perms_card = QFrame()
        perms_card.setObjectName("Card")
        self.perms_layout = QVBoxLayout(perms_card)
        self.perms_title = self._label_bold("اختر دورًا لعرض صلاحياته")
        self.perms_layout.addWidget(self.perms_title)
        self.perms_grid_container = QWidget()
        self.perms_grid = QGridLayout(self.perms_grid_container)
        self.perms_layout.addWidget(self.perms_grid_container)

        save_perms_button = QPushButton("حفظ الصلاحيات")
        save_perms_button.setObjectName("Primary")
        save_perms_button.clicked.connect(self.save_permissions)
        self.perms_layout.addWidget(save_perms_button)
        self.perms_message = QLabel("")
        self.perms_layout.addWidget(self.perms_message)
        self.perms_layout.addStretch()
        layout.addWidget(perms_card, 2)

        self.roles = []
        self.selected_role_id = None
        self.permission_checkboxes = []  # (module_key, view_cb, add_cb, edit_cb, delete_cb)
        self.refresh_roles()
        return widget

    def refresh_roles(self):
        self.roles = user_service.get_roles()
        self.roles_list.clear()
        for r in self.roles:
            self.roles_list.addItem(r["name"])

    def add_role(self):
        name = self.new_role_edit.text().strip()
        if not name:
            return
        user_service.create_role(name)
        self.new_role_edit.clear()
        self.refresh_roles()
        self.refresh_roles_combo()
        try:
            if self.current_user:
                log_action('roles', None, 'ui_create_role', user_id=self.current_user.user_id, details=f'role={name}')
        except Exception:
            pass

    def show_permissions(self, item):
        row = self.roles_list.row(item)
        role = self.roles[row]
        self.selected_role_id = role["id"]
        self.perms_title.setText(f"صلاحيات الدور: {role['name']}")

        while self.perms_grid.count():
            child = self.perms_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.permission_checkboxes = []

        headers = ["الشاشة", "عرض", "إضافة", "تعديل", "حذف"]
        for col, h in enumerate(headers):
            label = QLabel(h)
            label.setStyleSheet("font-weight: bold;")
            self.perms_grid.addWidget(label, 0, col)

        matrix = user_service.get_permission_matrix(role["id"])
        for i, row_data in enumerate(matrix, start=1):
            self.perms_grid.addWidget(QLabel(row_data["display_name"]), i, 0)
            view_cb = QCheckBox()
            view_cb.setChecked(row_data["can_view"])
            add_cb = QCheckBox()
            add_cb.setChecked(row_data["can_add"])
            edit_cb = QCheckBox()
            edit_cb.setChecked(row_data["can_edit"])
            delete_cb = QCheckBox()
            delete_cb.setChecked(row_data["can_delete"])
            self.perms_grid.addWidget(view_cb, i, 1)
            self.perms_grid.addWidget(add_cb, i, 2)
            self.perms_grid.addWidget(edit_cb, i, 3)
            self.perms_grid.addWidget(delete_cb, i, 4)
            self.permission_checkboxes.append((row_data["module_key"], view_cb, add_cb, edit_cb, delete_cb))

    def save_permissions(self):
        if self.selected_role_id is None:
            return
        matrix = []
        for module_key, view_cb, add_cb, edit_cb, delete_cb in self.permission_checkboxes:
            matrix.append({
                "module_key": module_key, "can_view": view_cb.isChecked(), "can_add": add_cb.isChecked(),
                "can_edit": edit_cb.isChecked(), "can_delete": delete_cb.isChecked(),
            })
        user_service.save_permissions(self.selected_role_id, matrix)
        self.perms_message.setText("تم حفظ الصلاحيات")
        self.perms_message.setStyleSheet("color: #146C8E;")
        try:
            if self.current_user:
                log_action('role_permissions', self.selected_role_id, 'ui_save_permissions', user_id=self.current_user.user_id)
        except Exception:
            pass
