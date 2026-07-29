"""Service providing analytics and financial reports queries for doctors, referral sources, patients, and departments."""
from __future__ import annotations

from app.db import get_connection


def get_visits_in_range(start_date: str = None, end_date: str = None, only_outstanding: bool = False,
                        limit: int = 2000) -> list:
    """Returns the individual visits behind the Reports & Statistics KPI summary cards, for
    drill-down when a card is clicked."""
    conn = get_connection()
    try:
        sql = ("SELECT v.id, v.invoice_number, v.visit_date, v.total_amount, v.discount_amount, "
               "v.paid_amount, p.full_name patient_name FROM visits v "
               "JOIN patients p ON p.id = v.patient_id WHERE 1=1")
        params = []
        if start_date:
            sql += " AND date(v.visit_date) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(v.visit_date) <= ?"
            params.append(end_date)
        sql += " ORDER BY v.id DESC LIMIT ?"
        params.append(limit)

        rows = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        for r in rows:
            r["balance"] = r["total_amount"] - r["discount_amount"] - r["paid_amount"]
        if only_outstanding:
            rows = [r for r in rows if r["balance"] > 0.001]
        return rows
    finally:
        conn.close()


def _period_totals(conn, start_date: str, end_date: str) -> dict:
    # Compares whole calendar days via date(v.visit_date) rather than raw string bounds like
    # "... <= '2026-07-29 23:59:59'" - visit_date is stored with a 'T' separator ("...T12:20:37"),
    # and 'T' (0x54) sorts after ' ' (0x20), so a same-day upper bound with a space would exclude
    # every visit from that day entirely under plain string comparison.
    row = conn.execute(
        "SELECT COUNT(*) visit_count, COALESCE(SUM(total_amount), 0) revenue "
        "FROM visits WHERE date(visit_date) BETWEEN ? AND ?",
        (start_date, end_date),
    ).fetchone()
    return {"visit_count": row["visit_count"], "revenue": row["revenue"]}


def _pct_change(current: float, previous: float):
    if not previous:
        return None
    return (current - previous) / previous * 100


def get_period_comparison() -> dict:
    """Month-to-date vs the same day-range last month, and year-to-date vs the same day-range last
    year - for the "growth" panel in Reports & Statistics."""
    conn = get_connection()
    try:
        this_month_start = conn.execute("SELECT date('now', 'start of month')").fetchone()[0]
        today = conn.execute("SELECT date('now')").fetchone()[0]
        last_month_start = conn.execute("SELECT date('now', 'start of month', '-1 month')").fetchone()[0]
        last_month_same_day = conn.execute("SELECT date('now', '-1 month')").fetchone()[0]

        this_year_start = conn.execute("SELECT date('now', 'start of year')").fetchone()[0]
        last_year_start = conn.execute("SELECT date('now', 'start of year', '-1 year')").fetchone()[0]
        last_year_same_day = conn.execute("SELECT date('now', '-1 year')").fetchone()[0]

        month_current = _period_totals(conn, this_month_start, today)
        month_previous = _period_totals(conn, last_month_start, last_month_same_day)
        year_current = _period_totals(conn, this_year_start, today)
        year_previous = _period_totals(conn, last_year_start, last_year_same_day)

        return {
            "month": {
                "current": month_current, "previous": month_previous,
                "revenue_change_pct": _pct_change(month_current["revenue"], month_previous["revenue"]),
                "visits_change_pct": _pct_change(month_current["visit_count"], month_previous["visit_count"]),
            },
            "year": {
                "current": year_current, "previous": year_previous,
                "revenue_change_pct": _pct_change(year_current["revenue"], year_previous["revenue"]),
                "visits_change_pct": _pct_change(year_current["visit_count"], year_previous["visit_count"]),
            },
        }
    finally:
        conn.close()


def get_turnaround_time_analytics(start_date: str = None, end_date: str = None) -> list:
    """Average turnaround time (order creation -> reviewer approval) per test, derived entirely
    from existing audit_logs timestamps - no schema change needed. Only orders that have actually
    reached 'Reviewed' status are counted, since earlier stages don't have a completion time yet."""
    conn = get_connection()
    try:
        sql = (
            "SELECT t.id test_id, t.name test_name, d.name department_name, "
            "COUNT(*) completed_count, "
            "AVG((julianday(appr.timestamp) - julianday(created.timestamp)) * 24) avg_hours, "
            "MAX((julianday(appr.timestamp) - julianday(created.timestamp)) * 24) max_hours "
            "FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id "
            "LEFT JOIN departments d ON d.id = t.department_id "
            "JOIN audit_logs created ON created.table_name = 'visit_test_orders' "
            "  AND created.action = 'create' AND created.row_id = o.id "
            "JOIN audit_logs appr ON appr.table_name = 'visit_test_orders' "
            "  AND appr.action = 'review_approve' AND appr.row_id = o.id "
            "WHERE o.status = 'Reviewed'"
        )
        params = []
        if start_date:
            sql += " AND date(created.timestamp) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(created.timestamp) <= ?"
            params.append(end_date)
        sql += " GROUP BY t.id ORDER BY avg_hours DESC"

        return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
    finally:
        conn.close()


def get_top_referring_doctors(start_date: str = None, end_date: str = None, limit: int = 100) -> list:
    """Returns all doctors with visit counts, total revenue, discount, paid amount, and outstanding balance."""
    conn = get_connection()
    try:
        sql = """
            SELECT 
                d.id AS doctor_id,
                d.full_name AS doctor_name,
                COUNT(v.id) AS visit_count,
                COALESCE(SUM(v.total_amount), 0) AS total_amount,
                COALESCE(SUM(v.discount_amount), 0) AS total_discount,
                COALESCE(SUM(v.paid_amount), 0) AS total_paid,
                COALESCE(SUM(v.total_amount - v.discount_amount - v.paid_amount), 0) AS total_balance
            FROM doctors d
            LEFT JOIN visits v ON v.doctor_id = d.id
            WHERE (d.is_active = 1 OR v.id IS NOT NULL)

        """
        params = []
        if start_date:
            sql += " AND date(v.visit_date) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(v.visit_date) <= ?"
            params.append(end_date)
        sql += " GROUP BY d.id ORDER BY visit_count DESC, total_amount DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_doctor_patients_drilldown(doctor_id: int, start_date: str = None, end_date: str = None) -> list:
    """Returns all visits and patient details referred by a specific doctor."""
    conn = get_connection()
    try:
        sql = """
            SELECT 
                v.id AS visit_id,
                v.invoice_number,
                v.visit_date,
                p.id AS patient_id,
                p.full_name AS patient_name,
                p.phone AS patient_phone,
                v.total_amount,
                v.discount_amount,
                v.paid_amount,
                (v.total_amount - v.discount_amount - v.paid_amount) AS balance
            FROM visits v
            JOIN patients p ON p.id = v.patient_id
            WHERE v.doctor_id = ?
        """
        params = [doctor_id]
        if start_date:
            sql += " AND date(v.visit_date) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(v.visit_date) <= ?"
            params.append(end_date)
        sql += " ORDER BY v.id DESC"

        visits = [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        for v in visits:
            orders = conn.execute(
                "SELECT t.name AS test_name FROM visit_test_orders vto "
                "JOIN tests t ON t.id = vto.test_id WHERE vto.visit_id = ?",
                (v["visit_id"],)
            ).fetchall()
            v["tests_str"] = "، ".join([o["test_name"] for o in orders]) if orders else "غير محدد"
        return visits
    finally:
        conn.close()


def get_referral_sources_analytics(start_date: str = None, end_date: str = None) -> list:
    """Returns aggregated financial report per referral source."""
    conn = get_connection()
    try:
        sql = """
            SELECT 
                COALESCE(rs.name, 'مباشر (بدون جهة)') AS source_name,
                COUNT(v.id) AS visit_count,
                COALESCE(SUM(v.total_amount), 0) AS total_amount,
                COALESCE(SUM(v.discount_amount), 0) AS total_discount,
                COALESCE(SUM(v.paid_amount), 0) AS total_paid,
                COALESCE(SUM(v.total_amount - v.discount_amount - v.paid_amount), 0) AS total_balance
            FROM visits v
            LEFT JOIN referral_sources rs ON rs.id = v.referral_source_id
            WHERE 1=1
        """
        params = []
        if start_date:
            sql += " AND date(v.visit_date) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(v.visit_date) <= ?"
            params.append(end_date)
        sql += " GROUP BY v.referral_source_id ORDER BY total_amount DESC"

        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_department_revenue_breakdown(start_date: str = None, end_date: str = None) -> list:
    """Returns revenue breakdown per laboratory department."""
    conn = get_connection()
    try:
        sql = """
            SELECT 
                COALESCE(d.name, 'عام / غير محدد') AS department_name,
                COUNT(vto.id) AS order_count,
                COALESCE(SUM(vto.price), 0) AS total_revenue
            FROM visit_test_orders vto
            JOIN tests t ON t.id = vto.test_id
            LEFT JOIN departments d ON d.id = t.department_id
            JOIN visits v ON v.id = vto.visit_id
            WHERE 1=1
        """
        params = []
        if start_date:
            sql += " AND date(v.visit_date) >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date(v.visit_date) <= ?"
            params.append(end_date)
        sql += " GROUP BY d.id ORDER BY total_revenue DESC"

        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_staff_productivity_analytics(start_date: str = None, end_date: str = None) -> list:
    """Returns productivity metrics per staff member: patients registered, visits created, revenue/payments collected, and test results processed."""
    conn = get_connection()
    try:
        users = conn.execute(
            "SELECT u.id AS user_id, u.username, u.full_name, COALESCE(r.name, 'بدون دور') AS role_name "
            "FROM users u LEFT JOIN roles r ON r.id = u.role_id WHERE u.is_active = 1 ORDER BY u.username"
        ).fetchall()

        result = []
        for u in users:
            uid = u["user_id"]
            p_audit_sql = "SELECT COUNT(DISTINCT row_id) FROM audit_logs WHERE table_name = 'patients' AND action = 'create' AND user_id = ?"
            p_audit_params = [uid]
            if start_date:
                p_audit_sql += " AND date(timestamp) >= ?"
                p_audit_params.append(start_date)
            if end_date:
                p_audit_sql += " AND date(timestamp) <= ?"
                p_audit_params.append(end_date)
            audit_patients = conn.execute(p_audit_sql, tuple(p_audit_params)).fetchone()[0]

            if not start_date and not end_date:
                direct_patients = conn.execute("SELECT COUNT(*) FROM patients WHERE created_by_user_id = ?", (uid,)).fetchone()[0]
                total_patients = max(direct_patients, audit_patients)
            else:
                total_patients = audit_patients


            v_sql = (
                "SELECT COUNT(DISTINCT a.row_id), COALESCE(SUM(v.paid_amount), 0) "
                "FROM audit_logs a JOIN visits v ON v.id = a.row_id "
                "WHERE a.table_name = 'visits' AND a.action = 'create' AND a.user_id = ?"
            )
            v_params = [uid]
            if start_date:
                v_sql += " AND date(a.timestamp) >= ?"
                v_params.append(start_date)
            if end_date:
                v_sql += " AND date(a.timestamp) <= ?"
                v_params.append(end_date)
            v_row = conn.execute(v_sql, tuple(v_params)).fetchone()
            visits_created = v_row[0] or 0
            collected_payments = v_row[1] or 0.0

            r_sql = (
                "SELECT COUNT(DISTINCT a.row_id) FROM audit_logs a "
                "WHERE a.table_name = 'results' AND a.action IN ('save', 'approve') AND a.user_id = ?"
            )
            r_params = [uid]
            if start_date:
                r_sql += " AND date(a.timestamp) >= ?"
                r_params.append(start_date)
            if end_date:
                r_sql += " AND date(a.timestamp) <= ?"
                r_params.append(end_date)
            results_processed = conn.execute(r_sql, tuple(r_params)).fetchone()[0]

            result.append({
                "user_id": uid,
                "username": u["username"],
                "full_name": u["full_name"] or u["username"],
                "role_name": u["role_name"],
                "registered_patients": total_patients,
                "visits_created": visits_created,
                "collected_payments": collected_payments,
                "results_processed": results_processed,
            })
        return result
    finally:
        conn.close()


def get_staff_activity_drilldown(user_id: int, start_date: str = None, end_date: str = None) -> list:
    """Returns detailed patient registrations and visits created by a specific staff member."""
    conn = get_connection()
    try:
        sql = """
            SELECT 
                p.id AS patient_id,
                p.full_name AS patient_name,
                p.phone AS patient_phone,
                v.id AS visit_id,
                v.invoice_number,
                v.visit_date,
                v.total_amount,
                v.paid_amount,
                (v.total_amount - v.discount_amount - v.paid_amount) AS balance
            FROM patients p
            LEFT JOIN visits v ON v.patient_id = p.id
            WHERE p.created_by_user_id = ?
               OR p.id IN (
                   SELECT row_id FROM audit_logs 
                   WHERE table_name = 'patients' AND action = 'create' AND user_id = ?
               )
        """
        params = [user_id, user_id]
        if start_date:
            sql += " AND (date(v.visit_date) >= ? OR v.visit_date IS NULL)"
            params.append(start_date)
        if end_date:
            sql += " AND (date(v.visit_date) <= ? OR v.visit_date IS NULL)"
            params.append(end_date)
        sql += " ORDER BY p.id DESC"

        rows = conn.execute(sql, tuple(params)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("visit_id"):
                orders = conn.execute(
                    "SELECT t.name AS test_name FROM visit_test_orders vto "
                    "JOIN tests t ON t.id = vto.test_id WHERE vto.visit_id = ?",
                    (d["visit_id"],)
                ).fetchall()
                d["tests_str"] = "، ".join([o["test_name"] for o in orders]) if orders else "غير محدد"
            else:
                d["tests_str"] = "-"
            result.append(d)
        return result
    finally:
        conn.close()

