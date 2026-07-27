"""Login and current-session permission checks."""
from __future__ import annotations

import bcrypt

from app.db import get_connection


class CurrentUser:
    def __init__(self, user_id: int, username: str, full_name: str, role_id: int, role_name: str):
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.role_id = role_id
        self.role_name = role_name
        self._permissions = {}

    def load_permissions(self):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT module_key, can_view, can_add, can_edit, can_delete FROM role_permissions WHERE role_id = ?",
                (self.role_id,),
            ).fetchall()
            self._permissions = {r["module_key"]: dict(r) for r in rows}
        finally:
            conn.close()

    def can_view(self, module_key: str) -> bool:
        p = self._permissions.get(module_key)
        return bool(p and p["can_view"])

    def can_add(self, module_key: str) -> bool:
        p = self._permissions.get(module_key)
        return bool(p and p["can_add"])

    def can_edit(self, module_key: str) -> bool:
        p = self._permissions.get(module_key)
        return bool(p and p["can_edit"])


def login(username: str, password: str) -> CurrentUser | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT u.id, u.username, u.full_name, u.password_hash, u.is_active, u.role_id, r.name role_name "
            "FROM users u JOIN roles r ON r.id = u.role_id WHERE u.username = ?",
            (username,),
        ).fetchone()
        if row is None or not row["is_active"]:
            return None
        if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
            return None
        user = CurrentUser(row["id"], row["username"], row["full_name"], row["role_id"], row["role_name"])
        user.load_permissions()
        return user
    finally:
        conn.close()


def change_password(user_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None or not bcrypt.checkpw(current_password.encode("utf-8"), row["password_hash"].encode("utf-8")):
            return False, "كلمة المرور الحالية غير صحيحة"
        new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.commit()
        return True, "تم تغيير كلمة المرور بنجاح"
    finally:
        conn.close()
