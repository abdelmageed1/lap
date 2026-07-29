"""Specimen (sample) collection-stage tracking - separate from visit_test_orders.status, which
tracks result entry/review progress (Ordered -> InProgress -> Completed -> Reviewed). This tracks
the physical sample itself: has it been drawn, received in the lab, and is it being processed."""
from __future__ import annotations

from app.db import get_connection
from app.utils.audit import log_action

STAGES = ["NotCollected", "Collected", "ReceivedInLab", "InTesting", "Completed"]

STAGE_LABELS = {
    "NotCollected": "لم يتم السحب",
    "Collected": "تم السحب",
    "ReceivedInLab": "تم الاستلام بالمعمل",
    "InTesting": "جاري التحليل",
    "Completed": "مكتملة",
}


def next_stage(current: str) -> str | None:
    try:
        idx = STAGES.index(current)
    except ValueError:
        return STAGES[0]
    if idx + 1 >= len(STAGES):
        return None
    return STAGES[idx + 1]


def get_pending_specimens(query: str = "") -> list:
    """Every order whose specimen hasn't reached the final stage yet, for the tracking screen."""
    conn = get_connection()
    try:
        sql = (
            "SELECT o.id order_id, o.specimen_status, t.name test_name, "
            "p.full_name patient_name, v.invoice_number, v.visit_date "
            "FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id "
            "JOIN visits v ON v.id = o.visit_id "
            "JOIN patients p ON p.id = v.patient_id "
            "WHERE o.specimen_status != 'Completed'"
        )
        params = []
        if query:
            sql += " AND (p.full_name LIKE ? OR t.name LIKE ? OR CAST(v.invoice_number AS TEXT) LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like, like])
        sql += " ORDER BY v.id DESC"
        return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
    finally:
        conn.close()


def advance_specimen_status(order_id: int, user_id: int = None) -> tuple[bool, str]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT specimen_status FROM visit_test_orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            return False, "الطلب غير موجود"
        new_stage = next_stage(row["specimen_status"])
        if new_stage is None:
            return False, "العينة وصلت بالفعل للمرحلة الأخيرة"
        conn.execute("UPDATE visit_test_orders SET specimen_status = ? WHERE id = ?", (new_stage, order_id))
        try:
            log_action('visit_test_orders', order_id, 'specimen_status_update', user_id=user_id,
                       details=f"-> {new_stage}", conn=conn)
        except Exception:
            pass
        conn.commit()
        return True, STAGE_LABELS[new_stage]
    finally:
        conn.close()
