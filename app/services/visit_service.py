"""Patient registration, visit/invoice creation, payments, and visit history."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.db import get_connection
from app.utils.audit import log_action


def create_visit(patient: dict, doctor_id, referral_source_id, test_ids: list, discount: float,
                  initial_payment: float, existing_patient_id: int = None, user_id: int = None) -> dict:
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
                log_action('patients', patient_id, 'update', user_id=user_id, conn=conn)
            except Exception:
                pass
        else:
            cur = conn.execute(
                "INSERT INTO patients (full_name, title, gender, age_years, phone, created_by_user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (patient["full_name"], patient.get("title"), patient.get("gender", "Male"),
                 patient.get("age_years"), patient.get("phone"), user_id),
            )
            patient_id = cur.lastrowid
            try:
                log_action('patients', patient_id, 'create', user_id=user_id, conn=conn)
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
            log_action('visits', visit_id, 'create', user_id=user_id, conn=conn)
        except Exception:
            pass

        for test_id, price in order_prices:
            cur_o = conn.execute(
                "INSERT INTO visit_test_orders (visit_id, test_id, price, status) VALUES (?, ?, ?, 'Ordered')",
                (visit_id, test_id, price),
            )
            try:
                log_action('visit_test_orders', cur_o.lastrowid, 'create', user_id=user_id, conn=conn)
            except Exception:
                pass

        if initial_payment > 0:
            pay_cur = conn.execute(
                "INSERT INTO payments (visit_id, amount, paid_at) VALUES (?, ?, ?)",
                (visit_id, initial_payment, datetime.now().isoformat(timespec="seconds")),
            )
            try:
                log_action('payments', pay_cur.lastrowid, 'create', user_id=user_id, conn=conn)
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


def add_payment(visit_id: int, amount: float, user_id: int = None) -> None:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO payments (visit_id, amount, paid_at) VALUES (?, ?, ?)",
            (visit_id, amount, datetime.now().isoformat(timespec="seconds")),
        )
        conn.execute("UPDATE visits SET paid_amount = paid_amount + ? WHERE id = ?", (amount, visit_id))
        try:
            log_action('payments', cur.lastrowid, 'create', user_id=user_id, conn=conn)
            log_action('visits', visit_id, 'update', user_id=user_id, details=f'paid+={amount}', conn=conn)
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


def _resolve_patient_creator(conn, patient_dict: dict) -> str:
    """Finds username or full_name of the user who registered this patient (via created_by_user_id or audit logs)."""
    user_id = patient_dict.get("created_by_user_id")
    if user_id:
        u = conn.execute("SELECT username, full_name FROM users WHERE id = ?", (user_id,)).fetchone()
        if u:
            return f"{u['full_name']} ({u['username']})" if u['full_name'] else u['username']

    patient_id = patient_dict.get("id")
    if patient_id:
        audit = conn.execute(
            "SELECT u.username, u.full_name FROM audit_logs a "
            "JOIN users u ON u.id = a.user_id "
            "WHERE a.table_name = 'patients' AND a.row_id = ? AND a.action = 'create' "
            "ORDER BY a.id ASC LIMIT 1",
            (patient_id,)
        ).fetchone()
        if audit:
            return f"{audit['full_name']} ({audit['username']})" if audit['full_name'] else audit['username']

    return "غير محدد"


def search_patients(query: str = "", start_date: str = None, end_date: str = None, limit: int = 100):
    """Search patients by name or phone and/or date range of their visits."""
    conn = get_connection()
    try:
        query = (query or "").strip()
        sql = ["SELECT p.*, COUNT(v.id) visit_count, MAX(v.visit_date) last_visit FROM patients p"]

        if start_date or end_date:
            sql.append("INNER JOIN visits v ON v.patient_id = p.id")
        else:
            sql.append("LEFT JOIN visits v ON v.patient_id = p.id")

        where_clauses = []
        params = []

        if query:
            where_clauses.append("(p.full_name LIKE ? OR p.phone LIKE ? OR CAST(v.invoice_number AS TEXT) LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like, like])


        if start_date:
            where_clauses.append("v.visit_date >= ?")
            params.append(f"{start_date} 00:00:00")

        if end_date:
            where_clauses.append("v.visit_date <= ?")
            params.append(f"{end_date} 23:59:59")

        if where_clauses:
            sql.append("WHERE " + " AND ".join(where_clauses))

        sql.append("GROUP BY p.id ORDER BY p.id DESC LIMIT ?")
        params.append(limit)

        rows = conn.execute(" ".join(sql), tuple(params)).fetchall()
        result = []
        for r in rows:
            p = dict(r)
            p["created_by_name"] = _resolve_patient_creator(conn, p)
            result.append(p)
        return result
    finally:
        conn.close()


def get_patient_by_id(patient_id: int):
    """Retrieve full patient details by ID with visit count and last visit date."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT p.*, COUNT(v.id) visit_count, MAX(v.visit_date) last_visit FROM patients p "
            "LEFT JOIN visits v ON v.patient_id = p.id WHERE p.id = ? GROUP BY p.id", (patient_id,)
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        res["created_by_name"] = _resolve_patient_creator(conn, res)
        return res
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


def get_daily_trends(days: int = 7):
    """Returns daily visits count and revenue for the last N days."""
    conn = get_connection()
    try:
        results = []
        now = datetime.now()
        for i in range(days - 1, -1, -1):
            target_date = (now - timedelta(days=i)).date().isoformat()
            row = conn.execute(
                "SELECT COUNT(id) AS visits, COALESCE(SUM(paid_amount), 0.0) AS revenue "
                "FROM visits WHERE visit_date LIKE ?", (f"{target_date}%",)
            ).fetchone()
            results.append({
                "date": target_date[5:],
                "full_date": target_date,
                "visits": row["visits"] or 0,
                "revenue": row["revenue"] or 0.0
            })
        return results
    finally:
        conn.close()


def get_patient_journey(visit_id: int) -> list:
    """Return ordered list of test stages for a given visit.
    Each entry includes test name and current status from ``visit_test_orders``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.name AS test_name, vto.status
            FROM visit_test_orders vto
            JOIN tests t ON t.id = vto.test_id
            WHERE vto.visit_id = ?
            ORDER BY vto.id ASC
            """,
            (visit_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_top_requested_tests(limit: int = 5) -> list:
    """Returns top N requested tests and their order counts."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT t.name AS test_name, COUNT(vto.id) AS test_count "
            "FROM visit_test_orders vto "
            "JOIN tests t ON t.id = vto.test_id "
            "GROUP BY t.id ORDER BY test_count DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"test_name": r["test_name"], "count": r["test_count"]} for r in rows]
    finally:
        conn.close()


def delete_patient(patient_id: int, user_id: int = None) -> tuple[bool, str]:
    """Deletes a patient and all associated visits, test orders, result values, and payments."""
    conn = get_connection()
    try:
        patient = conn.execute("SELECT full_name FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not patient:
            return False, "المريض غير موجود"

        patient_name = patient["full_name"]

        visit_rows = conn.execute("SELECT id FROM visits WHERE patient_id = ?", (patient_id,)).fetchall()
        visit_ids = [v["id"] for v in visit_rows]

        if visit_ids:
            placeholders = ",".join("?" * len(visit_ids))
            conn.execute(f"DELETE FROM payments WHERE visit_id IN ({placeholders})", visit_ids)

            order_rows = conn.execute(f"SELECT id FROM visit_test_orders WHERE visit_id IN ({placeholders})", visit_ids).fetchall()
            order_ids = [o["id"] for o in order_rows]

            if order_ids:
                order_placeholders = ",".join("?" * len(order_ids))
                conn.execute(f"DELETE FROM result_values WHERE visit_test_order_id IN ({order_placeholders})", order_ids)

            conn.execute(f"DELETE FROM visit_test_orders WHERE visit_id IN ({placeholders})", visit_ids)
            conn.execute("DELETE FROM visits WHERE patient_id = ?", (patient_id,))

        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()

        try:
            log_action('patients', patient_id, 'delete', user_id=user_id, details=f"حذف المريض: {patient_name}")
        except Exception:
            pass

        return True, f"تم حذف المريض '{patient_name}' بنجاح"
    except Exception as e:
        conn.rollback()
        return False, f"حدث خطأ أثناء حذف المريض: {str(e)}"
    finally:
        conn.close()


def get_referral_financial_report(start_date: str = None, end_date: str = None) -> list:
    """Aggregates visits, total amounts, discounts, payments, and balances grouped by Referral Source and Doctor."""
    conn = get_connection()
    try:
        sql = """
            SELECT 
                COALESCE(rs.name, 'مباشر (بدون جهة)') AS referral_source,
                COALESCE(d.full_name, 'غير محدد') AS doctor_name,
                COUNT(v.id) AS visit_count,
                SUM(v.total_amount) AS total_amount,
                SUM(v.discount_amount) AS total_discount,
                SUM(v.paid_amount) AS total_paid,
                SUM(v.total_amount - v.discount_amount - v.paid_amount) AS total_balance
            FROM visits v
            LEFT JOIN referral_sources rs ON rs.id = v.referral_source_id
            LEFT JOIN doctors d ON d.id = v.doctor_id
            WHERE 1=1
        """
        params = []
        if start_date:
            sql += " AND v.visit_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            sql += " AND v.visit_date <= ?"
            params.append(f"{end_date} 23:59:59")
        sql += " GROUP BY v.referral_source_id, v.doctor_id ORDER BY total_amount DESC"

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def export_patients_data() -> list[dict]:
    """Returns a list of dictionary records containing full patient demographics and visit metadata for export."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT 
                p.id, p.full_name, p.phone, p.gender, p.age_years, p.title,
                COUNT(v.id) AS visit_count, MAX(v.visit_date) AS last_visit
            FROM patients p
            LEFT JOIN visits v ON v.patient_id = p.id
            GROUP BY p.id
            ORDER BY p.id DESC

        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def import_patients_data(patients_list: list[dict], current_user_id: int = None) -> tuple[int, int, str]:
    """Imports or updates patient records from a list of dicts with deduplication by phone/full_name.
    Returns (created_count, updated_count, message).
    """
    if not patients_list:
        return 0, 0, "لم يتم العثور على أية سجلات مرضى للاستيراد."

    conn = get_connection()
    created_count = 0
    updated_count = 0
    try:
        for p in patients_list:
            full_name = (p.get("full_name") or p.get("اسم المريض") or "").strip()
            phone = (p.get("phone") or p.get("رقم التليفون") or "").strip()
            gender = p.get("gender") or p.get("الجنس") or "Male"
            if gender in ("ذكر", "Male", "M"):
                gender = "Male"
            elif gender in ("أنثى", "Female", "F"):
                gender = "Female"

            age_years = p.get("age_years") or p.get("السن") or 0
            try:
                age_years = int(float(str(age_years)))
            except Exception:
                age_years = 0

            age_months = p.get("age_months") or 0
            try:
                age_months = int(float(str(age_months)))
            except Exception:
                age_months = 0

            title = p.get("title") or p.get("اللقب") or ""
            notes = p.get("notes") or p.get("ملاحظات") or ""

            if not full_name:
                continue

            # Deduplication check
            existing = None
            if phone:
                existing = conn.execute("SELECT id FROM patients WHERE phone = ?", (phone,)).fetchone()
            if not existing:
                existing = conn.execute("SELECT id FROM patients WHERE full_name = ?", (full_name,)).fetchone()

            if existing:
                conn.execute(
                    "UPDATE patients SET gender = ?, age_years = ?, title = ? WHERE id = ?",
                    (gender, age_years, title, existing["id"])
                )
                updated_count += 1
            else:
                conn.execute(
                    "INSERT INTO patients (full_name, phone, gender, age_years, title, created_by_user_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (full_name, phone, gender, age_years, title, current_user_id)
                )
                created_count += 1

        conn.commit()
        return created_count, updated_count, f"تمت العملية بنجاح: تم إضافة {created_count} مريض جديد وتحديث {updated_count} مريض سابق."
    except Exception as exc:
        conn.rollback()
        return 0, 0, f"حدث خطأ أثناء الاستيراد: {exc}"
    finally:
        conn.close()




