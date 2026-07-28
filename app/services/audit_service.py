"""Read access to the audit_logs table for the audit log viewer screen."""
from __future__ import annotations

from app.db import get_connection


def search_audit_logs(table_name: str = "", date_from: str = "", date_to: str = "",
                      user_id: int = None, action: str = "", limit: int = 300):
    conn = get_connection()
    try:
        sql = "SELECT a.*, u.username FROM audit_logs a LEFT JOIN users u ON u.id = a.user_id WHERE 1=1"
        params = []
        if table_name:
            sql += " AND a.table_name = ?"
            params.append(table_name)
        if date_from:
            sql += " AND a.timestamp >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND a.timestamp <= ?"
            params.append(date_to + "T23:59:59")
        if user_id:
            sql += " AND a.user_id = ?"
            params.append(user_id)
        if action:
            sql += " AND a.action = ?"
            params.append(action)
        sql += " ORDER BY a.id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def get_distinct_tables():
    conn = get_connection()
    try:
        return [r["table_name"] for r in conn.execute(
            "SELECT DISTINCT table_name FROM audit_logs ORDER BY table_name"
        ).fetchall()]
    finally:
        conn.close()


def get_distinct_actions():
    conn = get_connection()
    try:
        return [r["action"] for r in conn.execute(
            "SELECT DISTINCT action FROM audit_logs WHERE action IS NOT NULL AND action != '' ORDER BY action"
        ).fetchall()]
    finally:
        conn.close()


def get_audit_users():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT u.id, u.username, u.full_name FROM audit_logs a "
            "JOIN users u ON u.id = a.user_id ORDER BY u.username"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

