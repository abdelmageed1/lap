"""Departments, test catalog, parameters/reference ranges, prices, referral sources and doctors."""
from __future__ import annotations

import json
import os

from app.config import SEED_DATA_DIR
from app.db import get_connection
from app.utils.audit import log_action

_title_suggestions_cache = None


def get_title_suggestions():
    """The real list of patient-title choices (السيد/السيدة/الآنسة...) from the original Access
    dropdown, extracted to seed_data/patient-title-suggestions.json."""
    global _title_suggestions_cache
    if _title_suggestions_cache is None:
        path = os.path.join(SEED_DATA_DIR, "patient-title-suggestions.json")
        with open(path, "r", encoding="utf-8") as f:
            _title_suggestions_cache = json.load(f)
    return _title_suggestions_cache


def get_departments():
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM departments ORDER BY name").fetchall()]
    finally:
        conn.close()


def save_department(department: dict) -> int:
    conn = get_connection()
    try:
        if department.get("id"):
            conn.execute("UPDATE departments SET name=? WHERE id=?", (department["name"], department["id"]))
            department_id = department["id"]
        else:
            cur = conn.execute("INSERT INTO departments (name) VALUES (?)", (department["name"],))
            department_id = cur.lastrowid
        try:
            log_action('departments', department_id, 'save', conn=conn)
        except Exception:
            pass
        conn.commit()
        return department_id
    finally:
        conn.close()


def delete_department(department_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        in_use = conn.execute(
            "SELECT COUNT(*) c FROM tests WHERE department_id = ?", (department_id,)
        ).fetchone()["c"]
        if in_use > 0:
            return False, f"لا يمكن حذف القسم: مرتبط بـ{in_use} تحليل"
        conn.execute("DELETE FROM departments WHERE id = ?", (department_id,))
        try:
            log_action('departments', department_id, 'delete', conn=conn)
        except Exception:
            pass
        conn.commit()
        return True, "تم الحذف"
    finally:
        conn.close()


def search_tests(name_contains: str = "", department_id: int = None, include_inactive: bool = False):
    conn = get_connection()
    try:
        sql = ("SELECT t.*, d.name department_name FROM tests t "
               "LEFT JOIN departments d ON d.id = t.department_id WHERE 1=1")
        params = []
        if not include_inactive:
            sql += " AND t.is_active = 1"
        if name_contains:
            sql += " AND (t.name LIKE ? OR t.abbreviation LIKE ?)"
            like = f"%{name_contains}%"
            params += [like, like]
        if department_id:
            sql += " AND t.department_id = ?"
            params.append(department_id)
        sql += " ORDER BY t.name LIMIT 300"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def get_test_with_details(test_id: int):
    conn = get_connection()
    try:
        test = conn.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
        if test is None:
            return None
        test = dict(test)
        params = conn.execute(
            "SELECT * FROM test_parameters WHERE test_id = ? ORDER BY display_order", (test_id,)
        ).fetchall()
        test["parameters"] = []
        for p in params:
            p = dict(p)
            p["ranges"] = [dict(r) for r in conn.execute(
                "SELECT * FROM parameter_reference_ranges WHERE parameter_id = ?", (p["id"],)
            ).fetchall()]
            test["parameters"].append(p)
        test["prices"] = [dict(r) for r in conn.execute(
            "SELECT * FROM price_list_items WHERE test_id = ?", (test_id,)
        ).fetchall()]
        return test
    finally:
        conn.close()


def get_price(test_id: int, source_type: str) -> float:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT price FROM price_list_items WHERE test_id = ? AND source_type = ?",
            (test_id, source_type),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT price FROM price_list_items WHERE test_id = ? ORDER BY id LIMIT 1", (test_id,)
            ).fetchone()
        return row["price"] if row else 0.0
    finally:
        conn.close()


def save_test(test: dict, user_id: int = None) -> int:
    conn = get_connection()
    try:
        if test.get("id"):
            conn.execute(
                "UPDATE tests SET name=?, abbreviation=?, department_id=?, default_unit=?, "
                "turnaround_time=?, collection_instructions=?, is_active=? WHERE id=?",
                (test["name"], test.get("abbreviation"), test.get("department_id"), test.get("default_unit"),
                 test.get("turnaround_time"), test.get("collection_instructions"), test.get("is_active", 1),
                 test["id"]),
            )
            test_id = test["id"]
        else:
            cur = conn.execute(
                "INSERT INTO tests (name, abbreviation, department_id, default_unit, turnaround_time, "
                "collection_instructions, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (test["name"], test.get("abbreviation"), test.get("department_id"), test.get("default_unit"),
                 test.get("turnaround_time"), test.get("collection_instructions")),
            )
            test_id = cur.lastrowid
        try:
            log_action('tests', test_id, 'save', user_id=user_id, conn=conn)
        except Exception:
            pass
        conn.commit()
        return test_id
    finally:
        conn.close()


def deactivate_test(test_id: int, user_id: int = None) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE tests SET is_active = 0 WHERE id = ?", (test_id,))
        try:
            log_action('tests', test_id, 'deactivate', user_id=user_id, conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def save_parameter(param: dict) -> int:
    conn = get_connection()
    try:
        if param.get("id"):
            conn.execute(
                "UPDATE test_parameters SET name=?, unit=?, data_type=?, display_order=? WHERE id=?",
                (param["name"], param.get("unit"), param.get("data_type", "Numeric"),
                 param.get("display_order", 0), param["id"]),
            )
            param_id = param["id"]
        else:
            cur = conn.execute(
                "INSERT INTO test_parameters (test_id, name, unit, data_type, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (param["test_id"], param["name"], param.get("unit"), param.get("data_type", "Numeric"),
                 param.get("display_order", 0)),
            )
            param_id = cur.lastrowid
        try:
            log_action('test_parameters', param_id, 'save', conn=conn)
        except Exception:
            pass
        conn.commit()
        return param_id
    finally:
        conn.close()


def delete_parameter(parameter_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM test_parameters WHERE id = ?", (parameter_id,))
        try:
            log_action('test_parameters', parameter_id, 'delete', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def save_reference_range(rng: dict) -> int:
    conn = get_connection()
    try:
        if rng.get("id"):
            conn.execute(
                "UPDATE parameter_reference_ranges SET sex=?, age_from_years=?, age_to_years=?, "
                "low_value=?, high_value=?, normal_text=? WHERE id=?",
                (rng.get("sex", "Both"), rng.get("age_from_years", 0), rng.get("age_to_years", 120),
                 rng.get("low_value"), rng.get("high_value"), rng.get("normal_text"), rng["id"]),
            )
            range_id = rng["id"]
        else:
            cur = conn.execute(
                "INSERT INTO parameter_reference_ranges (parameter_id, sex, age_from_years, age_to_years, "
                "low_value, high_value, normal_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rng["parameter_id"], rng.get("sex", "Both"), rng.get("age_from_years", 0),
                 rng.get("age_to_years", 120), rng.get("low_value"), rng.get("high_value"),
                 rng.get("normal_text")),
            )
            range_id = cur.lastrowid
        try:
            log_action('parameter_reference_ranges', range_id, 'save', conn=conn)
        except Exception:
            pass
        conn.commit()
        return range_id
    finally:
        conn.close()


def delete_reference_range(range_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM parameter_reference_ranges WHERE id = ?", (range_id,))
        try:
            log_action('parameter_reference_ranges', range_id, 'delete', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def save_price(price: dict) -> int:
    """Creates or updates a price. If `price` has no "id" but a row already exists for the same
    (test_id, source_type) pair, that existing row is updated instead of inserting a duplicate -
    without this lookup, saving a price for the same test/source twice creates a second row each
    time, leaving stale duplicate prices behind.
    """
    conn = get_connection()
    try:
        price_id = price.get("id")
        if not price_id:
            existing = conn.execute(
                "SELECT id FROM price_list_items WHERE test_id = ? AND source_type = ?",
                (price["test_id"], price["source_type"]),
            ).fetchone()
            if existing:
                price_id = existing["id"]

        if price_id:
            conn.execute(
                "UPDATE price_list_items SET source_type=?, price=? WHERE id=?",
                (price["source_type"], price["price"], price_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO price_list_items (test_id, source_type, price) VALUES (?, ?, ?)",
                (price["test_id"], price["source_type"], price["price"]),
            )
            price_id = cur.lastrowid
        try:
            log_action('price_list_items', price_id, 'save', conn=conn)
        except Exception:
            pass
        conn.commit()
        return price_id
    finally:
        conn.close()


def delete_price(price_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM price_list_items WHERE id = ?", (price_id,))
        try:
            log_action('price_list_items', price_id, 'delete', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def get_referral_sources():
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM referral_sources WHERE is_active = 1 ORDER BY name"
        ).fetchall()]
    finally:
        conn.close()


def save_referral_source(name: str, source_id: int = None) -> int:
    conn = get_connection()
    try:
        if source_id:
            conn.execute("UPDATE referral_sources SET name=? WHERE id=?", (name, source_id))
            row_id = source_id
        else:
            cur = conn.execute("INSERT INTO referral_sources (name) VALUES (?)", (name,))
            row_id = cur.lastrowid
        try:
            log_action('referral_sources', row_id, 'save', conn=conn)
        except Exception:
            pass
        conn.commit()
        return row_id
    finally:
        conn.close()


def deactivate_referral_source(source_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE referral_sources SET is_active = 0 WHERE id = ?", (source_id,))
        try:
            log_action('referral_sources', source_id, 'deactivate', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def get_doctors():
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM doctors WHERE is_active = 1 ORDER BY full_name"
        ).fetchall()]
    finally:
        conn.close()


def save_doctor(full_name: str, doctor_id: int = None) -> int:
    conn = get_connection()
    try:
        if doctor_id:
            conn.execute("UPDATE doctors SET full_name=? WHERE id=?", (full_name, doctor_id))
            row_id = doctor_id
        else:
            cur = conn.execute("INSERT INTO doctors (full_name) VALUES (?)", (full_name,))
            row_id = cur.lastrowid
        try:
            log_action('doctors', row_id, 'save', conn=conn)
        except Exception:
            pass
        conn.commit()
        return row_id
    finally:
        conn.close()


def deactivate_doctor(doctor_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE doctors SET is_active = 0 WHERE id = ?", (doctor_id,))
        try:
            log_action('doctors', doctor_id, 'deactivate', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def get_lab_settings():
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM lab_settings WHERE id = 1").fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def save_lab_settings(settings: dict) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE lab_settings SET lab_name=?, tagline=?, address=?, phone_numbers=?, "
            "footer_signature1=?, footer_signature2=? WHERE id=1",
            (settings.get("lab_name"), settings.get("tagline"), settings.get("address"),
             settings.get("phone_numbers"), settings.get("footer_signature1"),
             settings.get("footer_signature2")),
        )
        try:
            log_action('lab_settings', 1, 'update', conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def get_settings_dashboard_data() -> dict:
    conn = get_connection()
    try:
        return {
            "lab_settings": get_lab_settings(),
            "departments": get_departments(),
            "referral_sources": get_referral_sources(),
            "doctors": get_doctors(),
        }
    finally:
        conn.close()
