"""Loads the reference data extracted from the original Access database (ahmed_lab.mdb) into a
fresh SQLite database: departments, the unified test catalog, prices, reference ranges, referral
sources, and the real multi-parameter panels (CBC, liver/kidney/lipid/thyroid profiles, etc.)."""
import json
import os
import re

import bcrypt

from app.config import SEED_DATA_DIR
from app.db import get_connection

MODULE_KEYS = [
    "Dashboard", "Reception", "Visits", "Results", "Catalog", "Pricing", "Settings", "Users",
    "Audit", "PatientHistory", "Backup", "Reports",
]



def _load(name: str):
    with open(os.path.join(SEED_DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _select_range(dto_ranges):
    return [
        {
            "sex": r.get("sex") or "Both",
            "age_from": r.get("ageFromYears", 0) or 0,
            "age_to": r.get("ageToYears", 120) or 120,
            "low": r.get("lowValue"),
            "high": r.get("highValue"),
            "unit": r.get("unit"),
            "normal_text": r.get("normalText"),
        }
        for r in dto_ranges
    ]


def seed_if_empty() -> None:
    conn = get_connection()
    try:
        has_roles = conn.execute("SELECT COUNT(*) c FROM roles").fetchone()["c"] > 0
        if not has_roles:
            _seed_roles_and_admin(conn)

        has_departments = conn.execute("SELECT COUNT(*) c FROM departments").fetchone()["c"] > 0
        if not has_departments:
            test_ids = _seed_catalog(conn)
            _seed_profiles(conn, test_ids)

        has_settings = conn.execute("SELECT COUNT(*) c FROM lab_settings").fetchone()["c"] > 0
        if not has_settings:
            conn.execute(
                "INSERT INTO lab_settings (id, lab_name, supervising_doctor_name, tagline, address, phone_numbers) "
                "VALUES (1, ?, ?, ?, ?, ?)",
                ("معمل نخبة", "د. مصطفى الزناتي", "معملك الطبي الموثوق", "", ""),
            )
            conn.commit()

        _ensure_reference_defaults(conn)
        _backfill_missing_module_permissions(conn)
        _backfill_new_profile_breakdowns(conn)
    finally:
        conn.close()


def _ensure_reference_defaults(conn) -> None:
    """Ensure the basic reference data needed by the settings page exists even for older DBs."""
    existing_sources = {r["name"] for r in conn.execute("SELECT name FROM referral_sources").fetchall()}
    for name in ["فردي", "تأمين", "جهة خارجية"]:
        if name not in existing_sources:
            conn.execute("INSERT INTO referral_sources (name, is_active) VALUES (?, 1)", (name,))
        else:
            conn.execute("UPDATE referral_sources SET is_active = 1 WHERE name = ?", (name,))

    existing_doctors = {r["full_name"] for r in conn.execute("SELECT full_name FROM doctors").fetchall()}
    for name in ["د. مصطفى الزناتي", "د. أحمد محمد", "د. سارة علي"]:
        if name not in existing_doctors:
            conn.execute("INSERT INTO doctors (full_name, is_active) VALUES (?, 1)", (name,))
        else:
            conn.execute("UPDATE doctors SET is_active = 1 WHERE full_name = ?", (name,))

    conn.commit()



def _backfill_missing_module_permissions(conn) -> None:
    """New module keys (e.g. "Audit") added after a database was first seeded would otherwise be
    invisible to every existing role - this adds any missing (role, module_key) permission rows on
    every startup so upgrading the app doesn't silently hide new screens from existing installs.
    Admin roles (full-access by convention: every module already granted) get the new module
    granted too; other roles get it added but denied, matching how a brand-new role starts out.
    """
    roles = conn.execute("SELECT id FROM roles").fetchall()
    for role in roles:
        role_id = role["id"]
        existing = {r["module_key"] for r in conn.execute(
            "SELECT module_key FROM role_permissions WHERE role_id = ?", (role_id,)
        ).fetchall()}
        is_full_access_role = existing and all(
            r["can_view"] and r["can_add"] and r["can_edit"] and r["can_delete"]
            for r in conn.execute(
                "SELECT can_view, can_add, can_edit, can_delete FROM role_permissions WHERE role_id = ?",
                (role_id,),
            ).fetchall()
        )
        for module_key in MODULE_KEYS:
            if module_key in existing:
                continue
            grant = 1 if is_full_access_role else 0
            conn.execute(
                "INSERT INTO role_permissions (role_id, module_key, can_view, can_add, can_edit, can_delete) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (role_id, module_key, grant, grant, grant, grant),
            )
    conn.commit()


def _backfill_new_profile_breakdowns(conn) -> None:
    """Ensure existing databases get new profile parameters added in this round.

    Rules (safe for production databases with existing patient results):
    - If a test still has only the generic single "النتيجة" parameter AND no
      result has been entered under it, replace it with the real breakdown from
      profiles.json.
    - If any result already exists for the test, leave it completely untouched.
    - If a specific named parameter (e.g. "Color Index") is missing from an
      otherwise-expanded test, add just that parameter without touching others.
    """
    profiles_data = _load("profiles.json")
    profile_map = {
        e["attachKey"]: e["parameters"]
        for e in profiles_data.get("profiles", [])
        if e.get("attachKey")  # skip entries that use "newTest" key instead
    }

    # Resolve attach keys to test_ids using the tests table
    tests = conn.execute("SELECT id, name FROM tests").fetchall()

    # Build a rough key→id map matching how attachKey values in profiles.json are derived from a
    # test's display name: lowercased, alphanumerics only. Stripping only spaces/hyphens/
    # underscores (as an earlier version of this function did) missed trailing punctuation - e.g.
    # the real catalog name "Thyroid Function." (note the period) normalized to
    # "thyroidfunction." which never matched the "thyroidfunction" attachKey, so an
    # already-installed database's Thyroid Function test silently never got its breakdown
    # parameters from this backfill. Caught by tests/test_seed_migration.py.
    def _to_key(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    test_key_to_id = {_to_key(t["name"]): t["id"] for t in tests}

    for attach_key, new_params in profile_map.items():
        test_id = test_key_to_id.get(attach_key)
        if test_id is None:
            continue

        existing_params = conn.execute(
            "SELECT id, name FROM test_parameters WHERE test_id = ?", (test_id,)
        ).fetchall()

        existing_names = {p["name"] for p in existing_params}

        # Case 1: still has only the generic "النتيجة" parameter → full replacement
        if len(existing_params) == 1 and list(existing_names)[0] == "النتيجة":
            param_id = existing_params[0]["id"]
            has_results = conn.execute(
                "SELECT COUNT(*) c FROM result_values WHERE parameter_id = ?", (param_id,)
            ).fetchone()["c"]
            if has_results > 0:
                continue  # data present – leave untouched

            conn.execute("DELETE FROM test_parameters WHERE test_id = ?", (test_id,))
            for p in new_params:
                param_cur = conn.execute(
                    "INSERT INTO test_parameters (test_id, name, unit, data_type, display_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (test_id, p["name"], p.get("unit"), p.get("dataType", "Numeric"),
                     p.get("displayOrder", 0)),
                )
                param_id = param_cur.lastrowid
                for r in p.get("ranges", []):
                    conn.execute(
                        "INSERT INTO parameter_reference_ranges "
                        "(parameter_id, sex, age_from_years, age_to_years, low_value, high_value, normal_text) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (param_id, r.get("sex", "Both"), r.get("ageFromYears", 0),
                         r.get("ageToYears", 120), r.get("lowValue"), r.get("highValue"),
                         r.get("normalText")),
                    )

        # Case 2: already expanded – add any individual missing parameters
        else:
            for p in new_params:
                if p["name"] in existing_names:
                    continue
                max_order = conn.execute(
                    "SELECT COALESCE(MAX(display_order), 0) mo FROM test_parameters WHERE test_id = ?",
                    (test_id,),
                ).fetchone()["mo"]
                param_cur = conn.execute(
                    "INSERT INTO test_parameters (test_id, name, unit, data_type, display_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (test_id, p["name"], p.get("unit"), p.get("dataType", "Numeric"),
                     max_order + 1),
                )
                param_id = param_cur.lastrowid
                for r in p.get("ranges", []):
                    conn.execute(
                        "INSERT INTO parameter_reference_ranges "
                        "(parameter_id, sex, age_from_years, age_to_years, low_value, high_value, normal_text) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (param_id, r.get("sex", "Both"), r.get("ageFromYears", 0),
                         r.get("ageToYears", 120), r.get("lowValue"), r.get("highValue"),
                         r.get("normalText")),
                    )

    conn.commit()


def _seed_roles_and_admin(conn) -> None:
    roles = {
        "مدير النظام": {m: (1, 1, 1, 1) for m in MODULE_KEYS},
        "مدير المعمل": {m: (1, 1, 1, 0) if m != "Users" else (1, 0, 0, 0) for m in MODULE_KEYS},
        "استقبال": {
            "Dashboard": (1, 0, 0, 0), "Reception": (1, 1, 1, 0), "Visits": (1, 1, 1, 0),
            "Catalog": (1, 0, 0, 0), "Pricing": (1, 0, 0, 0), "PatientHistory": (1, 0, 0, 0),
        },
        "فني معمل": {
            "Dashboard": (1, 0, 0, 0), "Reception": (1, 0, 0, 0), "Results": (1, 1, 1, 0),
            "Catalog": (1, 0, 0, 0), "PatientHistory": (1, 0, 0, 0),
        },
    }
    role_ids = {}
    for name in roles:
        cur = conn.execute("INSERT INTO roles (name) VALUES (?)", (name,))
        role_ids[name] = cur.lastrowid

    for name, perms in roles.items():
        role_id = role_ids[name]
        for module_key, (view, add, edit, delete) in perms.items():
            conn.execute(
                "INSERT INTO role_permissions (role_id, module_key, can_view, can_add, can_edit, can_delete) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (role_id, module_key, view, add, edit, delete),
            )

    admin_hash = bcrypt.hashpw(b"Admin@123", bcrypt.gensalt()).decode("utf-8")
    conn.execute(
        "INSERT INTO users (username, full_name, password_hash, role_id, is_active) VALUES (?, ?, ?, ?, 1)",
        ("admin", "مدير النظام", admin_hash, role_ids["مدير النظام"]),
    )
    conn.commit()


def _seed_catalog(conn) -> None:
    departments = _load("departments.json")
    tests = _load("tests.json")
    ranges = {r["testKey"]: r["ranges"] for r in _load("reference-ranges.json")}
    prices = _load("prices.json")
    sources = _load("referral-sources.json")

    dept_ids = {}
    for d in departments:
        cur = conn.execute("INSERT INTO departments (name) VALUES (?)", (d["name"],))
        dept_ids[d["name"]] = cur.lastrowid

    for s in sources:
        conn.execute("INSERT OR IGNORE INTO referral_sources (name) VALUES (?)", (s["name"],))

    test_ids = {}
    for i, dto in enumerate(tests):
        dept_id = dept_ids.get(dto.get("department"))
        test_ranges = ranges.get(dto["key"])
        has_numeric = bool(test_ranges) and any(
            r.get("lowValue") is not None and r.get("highValue") is not None for r in test_ranges
        )
        unit = dto.get("defaultUnit")
        if not unit and test_ranges:
            unit = next((r.get("unit") for r in test_ranges if r.get("unit")), None)

        abbreviation = dto.get("abbreviation") or dto["name"][:30]
        cur = conn.execute(
            "INSERT INTO tests (name, abbreviation, department_id, default_unit, turnaround_time, "
            "collection_instructions, is_active, display_order) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (dto["name"], abbreviation, dept_id, unit, dto.get("turnaroundTime"),
             dto.get("collectionInstructions"), i),
        )
        test_id = cur.lastrowid
        test_ids[dto["key"]] = test_id

        param_cur = conn.execute(
            "INSERT INTO test_parameters (test_id, name, unit, data_type, display_order) VALUES (?, ?, ?, ?, 0)",
            (test_id, "النتيجة", unit, "Numeric" if has_numeric else "Text"),
        )
        param_id = param_cur.lastrowid

        for r in _select_range(test_ranges or []):
            conn.execute(
                "INSERT INTO parameter_reference_ranges (parameter_id, sex, age_from_years, age_to_years, "
                "low_value, high_value, normal_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (param_id, r["sex"], r["age_from"], r["age_to"], r["low"], r["high"], r["normal_text"]),
            )

    for p in prices:
        test_id = test_ids.get(p.get("testKey"))
        if test_id is None:
            continue
        source_type = p["sourceType"].strip()
        source_type = source_type[0].upper() + source_type[1:] if source_type else "Individual"
        conn.execute(
            "INSERT INTO price_list_items (test_id, source_type, price) VALUES (?, ?, ?)",
            (test_id, source_type, p["price"]),
        )

    conn.commit()
    return test_ids


def _seed_profiles(conn, test_id_by_key) -> None:
    """Enriches existing tests (CBC, liver/kidney/etc.) with their real multi-parameter breakdowns."""
    data = _load("profiles.json")

    for entry in data.get("profiles", []):
        attach_key = entry.get("attachKey")
        test_id = test_id_by_key.get(attach_key)
        if test_id is None:
            continue

        # Replace the generic single "النتيجة" parameter with the real breakdown.
        conn.execute("DELETE FROM test_parameters WHERE test_id = ?", (test_id,))

        for p in entry.get("parameters", []):
            param_cur = conn.execute(
                "INSERT INTO test_parameters (test_id, name, unit, data_type, display_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (test_id, p["name"], p.get("unit"), p.get("dataType", "Numeric"), p.get("displayOrder", 0)),
            )
            param_id = param_cur.lastrowid
            for r in p.get("ranges", []):
                conn.execute(
                    "INSERT INTO parameter_reference_ranges (parameter_id, sex, age_from_years, age_to_years, "
                    "low_value, high_value, normal_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (param_id, r.get("sex", "Both"), r.get("ageFromYears", 0), r.get("ageToYears", 120),
                     r.get("lowValue"), r.get("highValue"), r.get("normalText")),
                )

    dedupe = data.get("dedupe", {})
    for key in dedupe.get("deactivateKeys", []):
        test_id = test_id_by_key.get(key)
        if test_id:
            conn.execute("UPDATE tests SET is_active = 0 WHERE id = ?", (test_id,))

    conn.commit()
