"""Result entry: pending work list, per-parameter reference range resolution, flag computation.

Order status flows Ordered -> InProgress (draft) -> Completed (fully entered, awaiting review) ->
Reviewed (approved by a reviewer, printable). This is tracked entirely in the existing free-text
`status` column - no schema migration needed to add the review step."""
from __future__ import annotations

from app.db import get_connection
from app.utils.audit import log_action

STATUS_LABELS = {
    "Ordered": "بانتظار الإدخال",
    "InProgress": "مسودة (جارٍ الإدخال)",
    "Completed": "بانتظار المراجعة",
    "Reviewed": "معتمدة",
}

FLAG_LABELS = {"High": "مرتفع (H)", "Low": "منخفض (L)", "Abnormal": "غير طبيعي", "Normal": "طبيعي"}


def _select_range(ranges: list, sex: str, age_years: float):
    candidates = [r for r in ranges if r["sex"] in (sex, "Both")]
    candidates = [r for r in candidates if r["age_from_years"] <= age_years <= r["age_to_years"]]
    if not candidates:
        return None
    # Prefer a sex-specific match over "Both" when both are eligible.
    specific = [r for r in candidates if r["sex"] == sex]
    return specific[0] if specific else candidates[0]


def get_pending_orders(limit: int = 100, offset: int = 0):
    """Orders still being entered (not yet fully entered/sent for review)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT o.id, t.name test_name, p.full_name patient_name FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id JOIN visits v ON v.id = o.visit_id "
            "JOIN patients p ON p.id = v.patient_id WHERE o.status IN ('Ordered', 'InProgress') "
            "ORDER BY o.id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_orders_pending_review(limit: int = 100, offset: int = 0):
    """Orders fully entered and awaiting a reviewer's approval before they can be printed."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT o.id, t.name test_name, p.full_name patient_name FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id JOIN visits v ON v.id = o.visit_id "
            "JOIN patients p ON p.id = v.patient_id WHERE o.status = 'Completed' "
            "ORDER BY o.id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_order_entry_view(order_id: int):
    conn = get_connection()
    try:
        order = conn.execute(
            "SELECT o.*, t.name test_name, t.id test_id, v.id visit_id, p.full_name patient_name, "
            "p.gender, p.age_years FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id JOIN visits v ON v.id = o.visit_id "
            "JOIN patients p ON p.id = v.patient_id WHERE o.id = ?", (order_id,),
        ).fetchone()
        if order is None:
            return None
        order = dict(order)
        sex = order["gender"]
        age = order["age_years"] or 0

        params = conn.execute(
            "SELECT * FROM test_parameters WHERE test_id = ? ORDER BY display_order", (order["test_id"],)
        ).fetchall()

        existing = {r["parameter_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM result_values WHERE visit_test_order_id = ?", (order_id,)
        ).fetchall()}

        parameters = []
        for p in params:
            p = dict(p)
            ranges = [dict(r) for r in conn.execute(
                "SELECT * FROM parameter_reference_ranges WHERE parameter_id = ?", (p["id"],)
            ).fetchall()]
            matched = _select_range(ranges, sex, age)
            existing_value = existing.get(p["id"])
            parameters.append({
                "parameter_id": p["id"],
                "name": p["name"],
                "unit": p["unit"],
                "data_type": p["data_type"],
                "range_low": matched["low_value"] if matched else None,
                "range_high": matched["high_value"] if matched else None,
                "range_text": matched["normal_text"] if matched else None,
                "existing_numeric": existing_value["numeric_value"] if existing_value else None,
                "existing_text": existing_value["text_value"] if existing_value else None,
            })

        order["parameters"] = parameters
        return order
    finally:
        conn.close()


def _compute_flag(data_type: str, numeric_value, text_value, low, high, normal_text) -> str:
    if data_type == "Numeric" and numeric_value is not None:
        if low is not None and numeric_value < low:
            return "Low"
        if high is not None and numeric_value > high:
            return "High"
        return "Normal"
    if normal_text and text_value is not None and text_value.strip() != normal_text.strip():
        return "Abnormal"
    return "Normal"


def save_results(order_id: int, values: list, mark_completed: bool) -> None:
    """values: list of {parameter_id, numeric_value, text_value, low, high, normal_text, data_type}."""
    conn = get_connection()
    try:
        for v in values:
            flag = _compute_flag(v["data_type"], v.get("numeric_value"), v.get("text_value"),
                                  v.get("low"), v.get("high"), v.get("normal_text"))
            existing = conn.execute(
                "SELECT id FROM result_values WHERE visit_test_order_id = ? AND parameter_id = ?",
                (order_id, v["parameter_id"]),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE result_values SET numeric_value=?, text_value=?, flag=? WHERE id=?",
                    (v.get("numeric_value"), v.get("text_value"), flag, existing["id"]),
                )
                try:
                    log_action('result_values', existing['id'], 'update', conn=conn)
                except Exception:
                    pass
            else:
                cur = conn.execute(
                    "INSERT INTO result_values (visit_test_order_id, parameter_id, numeric_value, text_value, flag) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (order_id, v["parameter_id"], v.get("numeric_value"), v.get("text_value"), flag),
                )
                try:
                    log_action('result_values', cur.lastrowid, 'create', conn=conn)
                except Exception:
                    pass
        conn.execute(
            "UPDATE visit_test_orders SET status = ? WHERE id = ?",
            ("Completed" if mark_completed else "InProgress", order_id),
        )
        try:
            log_action('visit_test_orders', order_id, 'update', details=f'mark_completed={mark_completed}', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def get_report_data(order_id: int):
    """Everything needed to render the printed lab-result PDF for a (usually reviewed) order."""
    conn = get_connection()
    try:
        order = conn.execute(
            "SELECT o.id, o.status, t.name test_name, v.invoice_number, p.full_name patient_name, "
            "p.gender, p.age_years FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id JOIN visits v ON v.id = o.visit_id "
            "JOIN patients p ON p.id = v.patient_id WHERE o.id = ?", (order_id,),
        ).fetchone()
        if order is None:
            return None
        order = dict(order)
        sex = order["gender"]
        age = order["age_years"] or 0

        rows = conn.execute(
            "SELECT r.*, tp.name pname, tp.unit FROM result_values r "
            "JOIN test_parameters tp ON tp.id = r.parameter_id "
            "WHERE r.visit_test_order_id = ? ORDER BY tp.display_order", (order_id,),
        ).fetchall()
        parameters = []
        for r in rows:
            r = dict(r)
            ranges = [dict(x) for x in conn.execute(
                "SELECT * FROM parameter_reference_ranges WHERE parameter_id = ?", (r["parameter_id"],)
            ).fetchall()]
            matched = _select_range(ranges, sex, age)
            parameters.append({
                "name": r["pname"], "unit": r["unit"],
                "numeric_value": r["numeric_value"], "text_value": r["text_value"],
                "range_low": matched["low_value"] if matched else None,
                "range_high": matched["high_value"] if matched else None,
                "range_text": matched["normal_text"] if matched else None,
                "flag": r["flag"],
            })
        order["parameters"] = parameters
        return order
    finally:
        conn.close()


def approve_order(order_id: int, user_id=None) -> None:
    """Reviewer approval: the only transition that makes an order's result printable."""
    conn = get_connection()
    try:
        conn.execute("UPDATE visit_test_orders SET status = 'Reviewed' WHERE id = ?", (order_id,))
        try:
            log_action('visit_test_orders', order_id, 'review_approve', user_id=user_id, conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def send_back_for_edit(order_id: int, user_id=None) -> None:
    """Reviewer rejects the entered values and sends the order back to the entry queue."""
    conn = get_connection()
    try:
        conn.execute("UPDATE visit_test_orders SET status = 'InProgress' WHERE id = ?", (order_id,))
        try:
            log_action('visit_test_orders', order_id, 'review_reject', user_id=user_id, conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def get_patient_result_summary(patient_id: int):
    """Return a compact summary for a patient: whether any results are available and the latest test name."""
    conn = get_connection()
    try:
        latest = conn.execute(
            "SELECT o.id, t.name test_name FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id "
            "JOIN visits v ON v.id = o.visit_id "
            "WHERE v.patient_id = ? ORDER BY o.id DESC LIMIT 1",
            (patient_id,),
        ).fetchone()
        if latest is None:
            return {"has_results": False, "result_status": "غير متوفرة", "latest_test_name": None}

        order_id = latest["id"]
        has_results = conn.execute(
            "SELECT 1 FROM result_values WHERE visit_test_order_id = ? LIMIT 1",
            (order_id,),
        ).fetchone() is not None
        return {
            "has_results": has_results,
            "result_status": "متوفرة" if has_results else "غير متوفرة",
            "latest_test_name": latest["test_name"],
            "latest_order_id": order_id,
        }
    finally:
        conn.close()


def get_patient_history(patient_id: int, start_date: str = None, end_date: str = None):
    conn = get_connection()
    try:
        query = "SELECT * FROM visits WHERE patient_id = ?"
        params = [patient_id]
        if start_date:
            query += " AND visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
        query += " ORDER BY id DESC"

        visits = conn.execute(query, tuple(params)).fetchall()
        patient = conn.execute(
            "SELECT gender, age_years FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        sex = patient["gender"] if patient else None
        age = patient["age_years"] if patient and patient["age_years"] else 0

        history = []
        for v in visits:
            v = dict(v)
            orders = conn.execute(
                "SELECT o.id, t.name test_name FROM visit_test_orders o JOIN tests t ON t.id = o.test_id "
                "WHERE o.visit_id = ?", (v["id"],),
            ).fetchall()
            results = []
            for o in orders:
                rows = conn.execute(
                    "SELECT r.*, p.name parameter_name, p.unit FROM result_values r "
                    "JOIN test_parameters p ON p.id = r.parameter_id WHERE r.visit_test_order_id = ?",
                    (o["id"],),
                ).fetchall()
                for r in rows:
                    r = dict(r)
                    ranges = [dict(x) for x in conn.execute(
                        "SELECT * FROM parameter_reference_ranges WHERE parameter_id = ?", (r["parameter_id"],)
                    ).fetchall()]
                    matched = _select_range(ranges, sex, age)
                    r["range_low"] = matched["low_value"] if matched else None
                    r["range_high"] = matched["high_value"] if matched else None
                    r["range_text"] = matched["normal_text"] if matched else None
                    r["test_name"] = o["test_name"]
                    results.append(r)
            v["results"] = results
            history.append(v)
        return history
    finally:
        conn.close()
