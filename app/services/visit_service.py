"""Patient registration, visit/invoice creation, payments, and visit history."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.db import get_connection
from app.utils.audit import log_action


def create_visit(patient: dict, doctor_id, referral_source_id, test_ids: list, discount: float,
                  initial_payment: float, existing_patient_id: int = None) -> dict:
    """patient: {full_name, title, gender, age_years, phone}. Returns the created visit with invoice_number.

    If existing_patient_id is given (the receptionist picked a previously-registered patient, e.g.
    matched by phone), the visit is linked to that same patient row instead of creating a duplicate
    one - this is what lets get_patient_history() find all of a patient's past visits later."""
    if not patient.get("full_name", "").strip():
        raise ValueError("اسم المريض مطلوب")
    if not isinstance(test_ids, list) or not test_ids:
        raise ValueError("يجب اختيار تحليل واحد على الأقل")
    if patient.get("phone"):
        phone = str(patient["phone"]).strip()
        if not phone.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("رقم التليفون يجب أن يحتوى على أرقام فقط")

    conn = get_connection()
    try:
        if existing_patient_id:
            conn.execute(
                "UPDATE patients SET full_name=?, title=?, gender=?, age_years=?, phone=? WHERE id=?",
                (patient["full_name"], patient.get("title"), patient.get("gender", "Male"),
                 patient.get("age_years"), patient.get("phone"), existing_patient_id),
            )
            patient_id = existing_patient_id
            try:
                log_action('patients', patient_id, 'update', conn=conn)
            except Exception:
                pass
        else:
            cur = conn.execute(
                "INSERT INTO patients (full_name, title, gender, age_years, phone) VALUES (?, ?, ?, ?, ?)",
                (patient["full_name"], patient.get("title"), patient.get("gender", "Male"),
                 patient.get("age_years"), patient.get("phone")),
            )
            patient_id = cur.lastrowid
            try:
                log_action('patients', patient_id, 'create', conn=conn)
            except Exception:
                pass
        source_row = conn.execute(
            "SELECT name FROM referral_sources WHERE id = ?", (referral_source_id,)
        ).fetchone() if referral_source_id else None
        source_type = source_row["name"] if source_row else "Individual"

        last_invoice = conn.execute("SELECT MAX(invoice_number) m FROM visits").fetchone()["m"] or 0
        invoice_number = last_invoice + 1

        total = 0.0
        order_prices = []
        for test_id in test_ids:
            price_row = conn.execute(
                "SELECT price FROM price_list_items WHERE test_id = ? AND source_type = ?",
                (test_id, source_type),
            ).fetchone()
            if price_row is None:
                price_row = conn.execute(
                    "SELECT price FROM price_list_items WHERE test_id = ? ORDER BY id LIMIT 1", (test_id,)
                ).fetchone()
            price = price_row["price"] if price_row else 0.0
            order_prices.append((test_id, price))
            total += price

        visit_cur = conn.execute(
            "INSERT INTO visits (patient_id, invoice_number, visit_date, doctor_id, referral_source_id, "
            "total_amount, discount_amount, paid_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (patient_id, invoice_number, datetime.now().isoformat(timespec="seconds"), doctor_id,
             referral_source_id, total, discount, initial_payment),
        )
        visit_id = visit_cur.lastrowid
        try:
            log_action('visits', visit_id, 'create', conn=conn)
        except Exception:
            pass

        for test_id, price in order_prices:
            cur_o = conn.execute(
                "INSERT INTO visit_test_orders (visit_id, test_id, price, status) VALUES (?, ?, ?, 'Ordered')",
                (visit_id, test_id, price),
            )
            try:
                log_action('visit_test_orders', cur_o.lastrowid, 'create', conn=conn)
            except Exception:
                pass

        if initial_payment > 0:
            pay_cur = conn.execute(
                "INSERT INTO payments (visit_id, amount, paid_at) VALUES (?, ?, ?)",
                (visit_id, initial_payment, datetime.now().isoformat(timespec="seconds")),
            )
            try:
                log_action('payments', pay_cur.lastrowid, 'create', conn=conn)
            except Exception:
                pass

        conn.commit()
        return {
            "id": visit_id, "invoice_number": invoice_number, "patient_id": patient_id,
            "patient_name": patient["full_name"], "total": total, "discount": discount,
            "paid": initial_payment, "balance": total - discount - initial_payment,
        }
    finally:
        conn.close()


def add_payment(visit_id: int, amount: float) -> None:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO payments (visit_id, amount, paid_at) VALUES (?, ?, ?)",
            (visit_id, amount, datetime.now().isoformat(timespec="seconds")),
        )
        conn.execute("UPDATE visits SET paid_amount = paid_amount + ? WHERE id = ?", (amount, visit_id))
        try:
            log_action('payments', cur.lastrowid, 'create', conn=conn)
            log_action('visits', visit_id, 'update', details=f'paid+={amount}', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def search_visits(name_contains: str = "", unpaid_only: bool = False, limit: int = 100, offset: int = 0):
    conn = get_connection()
    try:
        sql = ("SELECT v.*, p.full_name patient_name, p.phone, p.gender, p.age_years FROM visits v "
               "JOIN patients p ON p.id = v.patient_id WHERE 1=1")
        params = []
        if name_contains:
            term = f"%{name_contains}%"
            sql += " AND (p.full_name LIKE ? OR p.phone LIKE ? OR CAST(v.invoice_number AS TEXT) LIKE ? OR CAST(v.visit_date AS TEXT) LIKE ?)"
            params.extend([term, term, term, term])
        sql += " ORDER BY v.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for r in rows:
            r["balance"] = r["total_amount"] - r["discount_amount"] - r["paid_amount"]
        if unpaid_only:
            rows = [r for r in rows if r["balance"] > 0.001]
        return rows
    finally:
        conn.close()


def get_visit_details(visit_id: int):
    conn = get_connection()
    try:
        visit = conn.execute(
            "SELECT v.*, p.full_name patient_name, p.title, p.gender, p.age_years, p.phone, "
            "d.full_name doctor_name, rs.name source_name FROM visits v "
            "JOIN patients p ON p.id = v.patient_id "
            "LEFT JOIN doctors d ON d.id = v.doctor_id "
            "LEFT JOIN referral_sources rs ON rs.id = v.referral_source_id "
            "WHERE v.id = ?", (visit_id,),
        ).fetchone()
        if visit is None:
            return None
        visit = dict(visit)
        visit["balance"] = visit["total_amount"] - visit["discount_amount"] - visit["paid_amount"]
        orders = conn.execute(
            "SELECT o.*, t.name test_name, d.name department_name FROM visit_test_orders o "
            "JOIN tests t ON t.id = o.test_id LEFT JOIN departments d ON d.id = t.department_id "
            "WHERE o.visit_id = ?", (visit_id,),
        ).fetchall()
        visit["orders"] = [dict(o) for o in orders]
        return visit
    finally:
        conn.close()


def dashboard_snapshot():
    conn = get_connection()
    try:
        today_date = datetime.now().date()
        today = today_date.isoformat()
        week_start = (today_date - timedelta(days=6)).isoformat()
        current_month = today[:7]

        visits_today = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(paid_amount),0) s FROM visits WHERE visit_date LIKE ?",
            (f"{today}%",),
        ).fetchone()
        visits_week = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(paid_amount),0) s FROM visits WHERE visit_date >= ? AND visit_date <= ?",
            (week_start, today),
        ).fetchone()
        visits_month = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(paid_amount),0) s FROM visits WHERE visit_date LIKE ?",
            (f"{current_month}%",),
        ).fetchone()
        outstanding = conn.execute(
            "SELECT COALESCE(SUM(total_amount - discount_amount - paid_amount),0) s FROM visits"
        ).fetchone()["s"]
        pending_results = conn.execute(
            "SELECT COUNT(*) c FROM visit_test_orders WHERE status != 'Reviewed'"
        ).fetchone()["c"]
        total_patients = conn.execute("SELECT COUNT(*) c FROM patients").fetchone()["c"]
        return {
            "visits_today": visits_today["c"],
            "revenue_today": visits_today["s"],
            "visits_week": visits_week["c"],
            "revenue_week": visits_week["s"],
            "visits_month": visits_month["c"],
            "revenue_month": visits_month["s"],
            "outstanding": outstanding,
            "pending_results": pending_results,
            "total_patients": total_patients,
        }
    finally:
        conn.close()


def get_todays_visits():
    conn = get_connection()
    try:
        today = datetime.now().date().isoformat()
        rows = conn.execute(
            "SELECT v.id, v.invoice_number, v.visit_date, v.total_amount, v.paid_amount, "
            "p.full_name patient_name FROM visits v JOIN patients p ON p.id = v.patient_id "
            "WHERE v.visit_date LIKE ? ORDER BY v.id DESC", (f"{today}%",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_todays_payments():
    conn = get_connection()
    try:
        today = datetime.now().date().isoformat()
        rows = conn.execute(
            "SELECT pay.amount, pay.paid_at, v.invoice_number, p.full_name patient_name "
            "FROM payments pay JOIN visits v ON v.id = pay.visit_id JOIN patients p ON p.id = v.patient_id "
            "WHERE pay.paid_at LIKE ? ORDER BY pay.id DESC", (f"{today}%",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_outstanding_visits(limit: int = 200):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT v.id, v.invoice_number, v.total_amount, v.discount_amount, v.paid_amount, "
            "p.full_name patient_name FROM visits v JOIN patients p ON p.id = v.patient_id "
            "WHERE (v.total_amount - v.discount_amount - v.paid_amount) > 0.001 "
            "ORDER BY v.id DESC LIMIT ?", (limit,),
        ).fetchall()
        result = []
        for r in rows:
            r = dict(r)
            r["balance"] = r["total_amount"] - r["discount_amount"] - r["paid_amount"]
            result.append(r)
        return result
    finally:
        conn.close()


def get_recent_patients(limit: int = 200):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT p.id, p.full_name, p.phone, COUNT(v.id) visit_count, MAX(v.visit_date) last_visit "
            "FROM patients p LEFT JOIN visits v ON v.patient_id = p.id "
            "GROUP BY p.id ORDER BY p.id DESC LIMIT ?", (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_patients(query: str = "", limit: int = 100):
    """Search patients by name or phone, with their visit count - powers the Patient History screen."""
    conn = get_connection()
    try:
        query = (query or "").strip()
        base = ("SELECT p.*, COUNT(v.id) visit_count, MAX(v.visit_date) last_visit FROM patients p "
                "LEFT JOIN visits v ON v.patient_id = p.id ")
        if query:
            like = f"%{query}%"
            rows = conn.execute(
                base + "WHERE p.full_name LIKE ? OR p.phone LIKE ? GROUP BY p.id ORDER BY p.id DESC LIMIT ?",
                (like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(base + "GROUP BY p.id ORDER BY p.id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def find_patients_by_phone(phone: str):
    """Used at reception to detect an existing patient and avoid creating a duplicate record."""
    conn = get_connection()
    try:
        phone = (phone or "").strip()
        if not phone:
            return []
        rows = conn.execute(
            "SELECT * FROM patients WHERE phone = ? ORDER BY id DESC", (phone,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
