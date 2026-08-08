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


def search_tests(name_contains: str = "", department_id: int = None, include_inactive: bool = False,
                 limit: int = 300, offset: int = 0):
    """Search tests with optional limit/offset for pagination.

    Defaults to `limit=300` to preserve previous behaviour when callers don't pass limits.
    """
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
        sql += " ORDER BY t.name"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params += [limit, offset]
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def count_tests(name_contains: str = "", department_id: int = None, include_inactive: bool = False) -> int:
    """Return the total number of tests matching the filters (ignores pagination)."""
    conn = get_connection()
    try:
        sql = "SELECT COUNT(*) c FROM tests WHERE 1=1"
        params = []
        if not include_inactive:
            sql += " AND is_active = 1"
        if name_contains:
            sql += " AND (name LIKE ? OR abbreviation LIKE ?)"
            like = f"%{name_contains}%"
            params += [like, like]
        if department_id:
            sql += " AND department_id = ?"
            params.append(department_id)
        return conn.execute(sql, params).fetchone()["c"]
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


def save_lab_settings(settings: dict, user_id: int = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE lab_settings SET lab_name=?, supervising_doctor_name=?, tagline=?, address=?, "
            "phone_numbers=?, footer_signature1=?, footer_signature2=?, digital_seal_text=?, "
            "app_title=?, brand_primary_color=?, brand_secondary_color=?, lab_name_font_size=?, "
            "periodic_report_enabled=?, periodic_report_frequency=?, periodic_report_last_sent=?, "
            "smtp_host=?, smtp_port=?, smtp_username=?, smtp_password=?, smtp_from_email=?, "
            "smtp_to_email=?, pdf_paper_mode=?, pdf_page_size=?, pdf_top_margin_mm=?, "
            "pdf_bottom_margin_mm=?, pdf_left_margin_mm=?, pdf_right_margin_mm=?, "
            "pdf_logo_align=?, pdf_header_show_logo=?, pdf_show_doctor_signature=?, "
            "pdf_doctor_signature_title=?, pdf_doctor_signature_path=?, pdf_show_stamp=?, "
            "pdf_stamp_path=?, pdf_custom_footer_notes=? WHERE id=1",
            (settings.get("lab_name"), settings.get("supervising_doctor_name"), settings.get("tagline"),
             settings.get("address"), settings.get("phone_numbers"), settings.get("footer_signature1"),
             settings.get("footer_signature2"), settings.get("digital_seal_text"),
             settings.get("app_title"), settings.get("brand_primary_color", "#0B4F6C"),
             settings.get("brand_secondary_color", "#146C8E"), settings.get("lab_name_font_size", 20),
             int(bool(settings.get("periodic_report_enabled"))), settings.get("periodic_report_frequency", "monthly"),
             settings.get("periodic_report_last_sent"),
             settings.get("smtp_host"), settings.get("smtp_port") or None,
             settings.get("smtp_username"), settings.get("smtp_password"),
             settings.get("smtp_from_email"), settings.get("smtp_to_email"),
             settings.get("pdf_paper_mode", "white_paper"), settings.get("pdf_page_size", "A4"),
             float(settings.get("pdf_top_margin_mm", 15.0) or 15.0),
             float(settings.get("pdf_bottom_margin_mm", 15.0) or 15.0),
             float(settings.get("pdf_left_margin_mm", 12.0) or 12.0),
             float(settings.get("pdf_right_margin_mm", 12.0) or 12.0),
             settings.get("pdf_logo_align", "right"), int(bool(settings.get("pdf_header_show_logo", 1))),
             int(bool(settings.get("pdf_show_doctor_signature", 1))),
             settings.get("pdf_doctor_signature_title", "طبيب التحاليل المسؤول"),
             settings.get("pdf_doctor_signature_path", ""), int(bool(settings.get("pdf_show_stamp", 1))),
             settings.get("pdf_stamp_path", ""), settings.get("pdf_custom_footer_notes", "")),
        )
        try:
            log_action('lab_settings', 1, 'update', user_id=user_id, conn=conn)
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()




def get_catalog_dashboard_stats() -> dict:
    conn = get_connection()
    try:
        total_tests = conn.execute("SELECT COUNT(*) c FROM tests").fetchone()["c"]
        active_tests = conn.execute("SELECT COUNT(*) c FROM tests WHERE is_active = 1").fetchone()["c"]
        inactive_tests = conn.execute("SELECT COUNT(*) c FROM tests WHERE is_active = 0").fetchone()["c"]
        total_departments = conn.execute("SELECT COUNT(*) c FROM departments").fetchone()["c"]
        total_referral_sources = conn.execute("SELECT COUNT(*) c FROM referral_sources WHERE is_active = 1").fetchone()["c"]
        total_doctors = conn.execute("SELECT COUNT(*) c FROM doctors WHERE is_active = 1").fetchone()["c"]
        return {
            "total_tests": total_tests,
            "active_tests": active_tests,
            "inactive_tests": inactive_tests,
            "total_departments": total_departments,
            "total_referral_sources": total_referral_sources,
            "total_doctors": total_doctors,
        }
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


# ---------------------------------------------------------------------------
# Catalog Export & Import
# ---------------------------------------------------------------------------

def export_catalog_to_json(path: str) -> tuple[int, str]:
    """Export all departments, tests, parameters, reference ranges and prices to a JSON file.
    Returns (total_tests_exported, message).
    """
    conn = get_connection()
    try:
        departments = [dict(r) for r in conn.execute("SELECT * FROM departments ORDER BY name").fetchall()]
        tests = [dict(r) for r in conn.execute(
            "SELECT * FROM tests ORDER BY name"
        ).fetchall()]
        for t in tests:
            tid = t["id"]
            params = [dict(p) for p in conn.execute(
                "SELECT * FROM test_parameters WHERE test_id = ? ORDER BY display_order", (tid,)
            ).fetchall()]
            for p in params:
                p["ranges"] = [dict(r) for r in conn.execute(
                    "SELECT * FROM parameter_reference_ranges WHERE parameter_id = ?", (p["id"],)
                ).fetchall()]
            t["parameters"] = params
            t["prices"] = [dict(pr) for pr in conn.execute(
                "SELECT source_type, price FROM price_list_items WHERE test_id = ?", (tid,)
            ).fetchall()]
    finally:
        conn.close()

    catalog = {
        "__version": "1.0",
        "__exported_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "departments": departments,
        "tests": tests,
    }
    import os
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        __import__("json").dump(catalog, f, ensure_ascii=False, indent=2)
    return len(tests), f"تم تصدير {len(tests)} تحليل و{len(departments)} قسم بنجاح."


def import_catalog_from_json(path: str, merge_mode: str = "add_and_update", user_id: int = None) -> tuple[int, int, list, str]:
    """Import catalog from a JSON file exported by export_catalog_to_json.

    Args:
        path: Path to the JSON file.
        merge_mode: "add_only" → skip existing tests; "add_and_update" → update existing too.

    Returns:
        (added_count, updated_count, errors_list, message)
    """
    import json as _json
    try:
        with open(path, "r", encoding="utf-8") as f:
            catalog = _json.load(f)
    except Exception as exc:
        return 0, 0, [], f"تعذر قراءة الملف: {exc}"

    departments_in = catalog.get("departments", [])
    tests_in = catalog.get("tests", [])

    conn = get_connection()
    added = 0
    updated = 0
    errors = []

    try:
        # 1. Ensure departments exist (by name)
        dept_name_to_id = {}
        for d in conn.execute("SELECT id, name FROM departments").fetchall():
            dept_name_to_id[d["name"]] = d["id"]

        for dept in departments_in:
            dname = (dept.get("name") or "").strip()
            if not dname:
                continue
            if dname not in dept_name_to_id:
                cur = conn.execute("INSERT INTO departments (name) VALUES (?)", (dname,))
                dept_name_to_id[dname] = cur.lastrowid

        # 2. Import tests
        for t in tests_in:
            tname = (t.get("name") or "").strip()
            if not tname:
                continue
            try:
                # Remap department
                old_dept_id = t.get("department_id")
                dept_name = None
                for d in departments_in:
                    if d.get("id") == old_dept_id:
                        dept_name = d.get("name")
                        break
                new_dept_id = dept_name_to_id.get(dept_name) if dept_name else None

                existing = conn.execute("SELECT id FROM tests WHERE name = ?", (tname,)).fetchone()

                if existing:
                    if merge_mode == "add_and_update":
                        tid = existing["id"]
                        conn.execute(
                            "UPDATE tests SET abbreviation=?, department_id=?, default_unit=?, "
                            "turnaround_time=?, collection_instructions=?, is_active=1 WHERE id=?",
                            (t.get("abbreviation"), new_dept_id, t.get("default_unit"),
                             t.get("turnaround_time"), t.get("collection_instructions"), tid)
                        )
                        updated += 1
                    else:
                        continue  # add_only: skip
                else:
                    cur = conn.execute(
                        "INSERT INTO tests (name, abbreviation, department_id, default_unit, "
                        "turnaround_time, collection_instructions, is_active) VALUES (?,?,?,?,?,?,1)",
                        (tname, t.get("abbreviation"), new_dept_id, t.get("default_unit"),
                         t.get("turnaround_time"), t.get("collection_instructions"))
                    )
                    tid = cur.lastrowid
                    added += 1

                # Re-insert parameters & ranges (delete old ones first on update)
                conn.execute("DELETE FROM parameter_reference_ranges WHERE parameter_id IN "
                             "(SELECT id FROM test_parameters WHERE test_id = ?)", (tid,))
                conn.execute("DELETE FROM test_parameters WHERE test_id = ?", (tid,))
                for order_i, p in enumerate(t.get("parameters", [])):
                    pcur = conn.execute(
                        "INSERT INTO test_parameters (test_id, name, unit, display_order) VALUES (?,?,?,?)",
                        (tid, p.get("name"), p.get("unit"), p.get("display_order", order_i))
                    )
                    pid = pcur.lastrowid
                    for rng in p.get("ranges", []):
                        conn.execute(
                            "INSERT INTO parameter_reference_ranges "
                            "(parameter_id, sex, age_from_years, age_to_years, low_value, high_value, normal_text) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (pid, rng.get("sex", "Both"), rng.get("age_from_years", 0),
                             rng.get("age_to_years", 120), rng.get("low_value"),
                             rng.get("high_value"), rng.get("normal_text"))
                        )

                # Re-insert prices
                conn.execute("DELETE FROM price_list_items WHERE test_id = ?", (tid,))
                for pr in t.get("prices", []):
                    if pr.get("source_type") and pr.get("price") is not None:
                        conn.execute(
                            "INSERT INTO price_list_items (test_id, source_type, price) VALUES (?,?,?)",
                            (tid, pr["source_type"], pr["price"])
                        )

            except Exception as exc:
                errors.append(f"خطأ في تحليل '{tname}': {exc}")

        conn.commit()
        msg = f"تم الاستيراد: {added} تحليل جديد، {updated} تحليل محدَّث"
        if errors:
            msg += f"، {len(errors)} خطأ."
        else:
            msg += " ✅"
        return added, updated, errors, msg

    except Exception as exc:
        conn.rollback()
        return 0, 0, [str(exc)], f"حدث خطأ عام أثناء الاستيراد: {exc}"
    finally:
        conn.close()

