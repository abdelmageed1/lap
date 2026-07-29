"""Staff check-in/check-out (attendance) tracking."""
from __future__ import annotations

from datetime import datetime

from app.db import get_connection


def get_open_session(user_id: int):
    """Returns the current in-progress (checked in, not yet checked out) session for this user,
    or None if they aren't currently checked in."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM attendance WHERE user_id = ? AND check_out IS NULL ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def check_in(user_id: int) -> tuple[bool, str]:
    if get_open_session(user_id):
        return False, "لديك تسجيل حضور مفتوح بالفعل - سجّل الانصراف أولًا"
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO attendance (user_id, check_in) VALUES (?, ?)",
            (user_id, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, "تم تسجيل الحضور بنجاح"
    finally:
        conn.close()


def check_out(user_id: int) -> tuple[bool, str]:
    open_session = get_open_session(user_id)
    if not open_session:
        return False, "لا يوجد تسجيل حضور مفتوح لتسجيل الانصراف منه"
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE attendance SET check_out = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), open_session["id"]),
        )
        conn.commit()
        return True, "تم تسجيل الانصراف بنجاح"
    finally:
        conn.close()


def get_attendance_report(start_date: str = None, end_date: str = None, user_id: int = None) -> list:
    """Every attendance record in range, with computed hours_worked (None while still checked in)."""
    conn = get_connection()
    try:
        sql = (
            "SELECT a.id, a.user_id, u.full_name, a.check_in, a.check_out "
            "FROM attendance a JOIN users u ON u.id = a.user_id WHERE 1=1"
        )
        params = []
        if user_id:
            sql += " AND a.user_id = ?"
            params.append(user_id)
        if start_date:
            sql += " AND date(a.check_in) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(a.check_in) <= ?"
            params.append(end_date)
        sql += " ORDER BY a.check_in DESC"

        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        for r in rows:
            if r["check_out"]:
                delta = datetime.fromisoformat(r["check_out"]) - datetime.fromisoformat(r["check_in"])
                r["hours_worked"] = round(delta.total_seconds() / 3600, 2)
            else:
                r["hours_worked"] = None
        return rows
    finally:
        conn.close()
