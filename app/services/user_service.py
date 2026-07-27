"""Users, roles and their per-module permissions."""
from __future__ import annotations

import bcrypt

from app.db import get_connection
from app.seed import MODULE_KEYS
from app.utils.audit import log_action

MODULE_DISPLAY_NAMES = {
    "Dashboard": "لوحة المتابعة",
    "Reception": "الاستقبال",
    "Visits": "الزيارات والفواتير",
    "Results": "نتائج التحاليل",
    "Catalog": "كتالوج التحاليل",
    "Pricing": "الأسعار",
    "Users": "المستخدمون والأدوار",
    "Audit": "سجل التدقيق",
    "PatientHistory": "سجل المريض",
    "Backup": "النسخ الاحتياطي والاستعادة",
}


def get_roles():
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM roles ORDER BY name").fetchall()]
    finally:
        conn.close()


def create_role(name: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO roles (name) VALUES (?)", (name,))
        role_id = cur.lastrowid
        for m in MODULE_KEYS:
            conn.execute(
                "INSERT INTO role_permissions (role_id, module_key, can_view, can_add, can_edit, can_delete) "
                "VALUES (?, ?, 0, 0, 0, 0)", (role_id, m),
            )
        conn.commit()
        # Audit
        try:
            log_action('roles', role_id, 'create')
        except Exception:
            pass
        return role_id
    finally:
        conn.close()


def delete_role(role_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        in_use = conn.execute("SELECT COUNT(*) c FROM users WHERE role_id = ?", (role_id,)).fetchone()["c"]
        if in_use > 0:
            return False, "لا يمكن حذف دور مرتبط بمستخدمين حاليين"
        conn.execute("DELETE FROM roles WHERE id = ?", (role_id,))
        conn.commit()
        try:
            log_action('roles', role_id, 'delete')
        except Exception:
            pass
        return True, "تم الحذف"
    finally:
        conn.close()


def get_permission_matrix(role_id: int):
    conn = get_connection()
    try:
        rows = {r["module_key"]: dict(r) for r in conn.execute(
            "SELECT * FROM role_permissions WHERE role_id = ?", (role_id,)
        ).fetchall()}
        matrix = []
        for m in MODULE_KEYS:
            existing = rows.get(m, {})
            matrix.append({
                "module_key": m,
                "display_name": MODULE_DISPLAY_NAMES.get(m, m),
                "can_view": bool(existing.get("can_view", 0)),
                "can_add": bool(existing.get("can_add", 0)),
                "can_edit": bool(existing.get("can_edit", 0)),
                "can_delete": bool(existing.get("can_delete", 0)),
            })
        return matrix
    finally:
        conn.close()


def save_permissions(role_id: int, matrix: list) -> None:
    conn = get_connection()
    try:
        for row in matrix:
            existing = conn.execute(
                "SELECT id FROM role_permissions WHERE role_id = ? AND module_key = ?",
                (role_id, row["module_key"]),
            ).fetchone()
            values = (int(row["can_view"]), int(row["can_add"]), int(row["can_edit"]), int(row["can_delete"]))
            if existing:
                conn.execute(
                    "UPDATE role_permissions SET can_view=?, can_add=?, can_edit=?, can_delete=? WHERE id=?",
                    values + (existing["id"],),
                )
            else:
                conn.execute(
                    "INSERT INTO role_permissions (role_id, module_key, can_view, can_add, can_edit, can_delete) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (role_id, row["module_key"]) + values,
                )
        conn.commit()
    finally:
        conn.close()


def get_users():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT u.id, u.username, u.full_name, u.is_active, r.name role_name, u.role_id "
            "FROM users u JOIN roles r ON r.id = u.role_id ORDER BY u.username"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_user(username: str, full_name: str, password: str, role_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return False, "اسم المستخدم موجود بالفعل"
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn.execute(
            "INSERT INTO users (username, full_name, password_hash, role_id, is_active) VALUES (?, ?, ?, ?, 1)",
            (username, full_name, password_hash, role_id),
        )
        cur = conn.execute("SELECT last_insert_rowid() AS id")
        conn.commit()
        try:
            user_id = cur.fetchone()["id"] if cur else None
            log_action('users', user_id, 'create')
        except Exception:
            pass
        return True, "تمت الإضافة بنجاح"
    finally:
        conn.close()


def set_user_active(user_id: int, is_active: bool) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(is_active), user_id))
        conn.commit()
        try:
            log_action('users', user_id, 'update', details=f'is_active={is_active}')
        except Exception:
            pass
    finally:
        conn.close()


def reset_password(user_id: int, new_password: str) -> None:
    conn = get_connection()
    try:
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
        try:
            log_action('users', user_id, 'update', details='password_reset')
        except Exception:
            pass
    finally:
        conn.close()
