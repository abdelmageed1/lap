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
            sql += " AND v.visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND v.visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
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
            sql += " AND v.visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND v.visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
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
            sql += " AND v.visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND v.visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
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
            sql += " AND v.visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND v.visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
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
            sql += " AND v.visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND v.visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
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
                p_audit_sql += " AND timestamp >= ?"
                p_audit_params.append(f"{start_date} 00:00:00")
            if end_date:
                p_audit_sql += " AND timestamp <= ?"
                p_audit_params.append(f"{end_date} 23:59:59")
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
                v_sql += " AND a.timestamp >= ?"
                v_params.append(f"{start_date} 00:00:00")
            if end_date:
                v_sql += " AND a.timestamp <= ?"
                v_params.append(f"{end_date} 23:59:59")
            v_row = conn.execute(v_sql, tuple(v_params)).fetchone()
            visits_created = v_row[0] or 0
            collected_payments = v_row[1] or 0.0

            r_sql = (
                "SELECT COUNT(DISTINCT a.row_id) FROM audit_logs a "
                "WHERE a.table_name = 'results' AND a.action IN ('save', 'approve') AND a.user_id = ?"
            )
            r_params = [uid]
            if start_date:
                r_sql += " AND a.timestamp >= ?"
                r_params.append(f"{start_date} 00:00:00")
            if end_date:
                r_sql += " AND a.timestamp <= ?"
                r_params.append(f"{end_date} 23:59:59")
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
            sql += " AND (v.visit_date >= ? OR v.visit_date IS NULL)"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND (v.visit_date <= ? OR v.visit_date IS NULL)"
            params.append(f"{end_date} 23:59:59")
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

