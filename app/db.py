"""SQLite connection helper and schema definition for the Python/Windows-7 edition of LapLIS."""
import sqlite3

from app.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    abbreviation TEXT,
    department_id INTEGER REFERENCES departments(id),
    default_unit TEXT,
    turnaround_time TEXT,
    collection_instructions TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    unit TEXT,
    data_type TEXT NOT NULL DEFAULT 'Numeric',
    display_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS parameter_reference_ranges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parameter_id INTEGER NOT NULL REFERENCES test_parameters(id) ON DELETE CASCADE,
    sex TEXT NOT NULL DEFAULT 'Both',
    age_from_years REAL NOT NULL DEFAULT 0,
    age_to_years REAL NOT NULL DEFAULT 120,
    low_value REAL,
    high_value REAL,
    normal_text TEXT
);

CREATE TABLE IF NOT EXISTS price_list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS referral_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    title TEXT,
    gender TEXT NOT NULL DEFAULT 'Male',
    age_years REAL,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    invoice_number INTEGER NOT NULL,
    visit_date TEXT NOT NULL,
    doctor_id INTEGER REFERENCES doctors(id),
    referral_source_id INTEGER REFERENCES referral_sources(id),
    total_amount REAL NOT NULL DEFAULT 0,
    discount_amount REAL NOT NULL DEFAULT 0,
    paid_amount REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS visit_test_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    test_id INTEGER NOT NULL REFERENCES tests(id),
    price REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Ordered',
    specimen_status TEXT NOT NULL DEFAULT 'NotCollected'
);

CREATE TABLE IF NOT EXISTS result_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_test_order_id INTEGER NOT NULL REFERENCES visit_test_orders(id) ON DELETE CASCADE,
    parameter_id INTEGER NOT NULL REFERENCES test_parameters(id),
    numeric_value REAL,
    text_value TEXT,
    flag TEXT NOT NULL DEFAULT 'Normal'
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    paid_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    module_key TEXT NOT NULL,
    can_view INTEGER NOT NULL DEFAULT 0,
    can_add INTEGER NOT NULL DEFAULT 0,
    can_edit INTEGER NOT NULL DEFAULT 0,
    can_delete INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id),
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS lab_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    lab_name TEXT NOT NULL,
    supervising_doctor_name TEXT,
    tagline TEXT,
    address TEXT,
    phone_numbers TEXT,
    footer_signature1 TEXT,
    footer_signature2 TEXT,
    digital_seal_text TEXT DEFAULT '🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً.',
    app_title TEXT DEFAULT 'LapLIS - نظام إدارة معمل التحاليل الطبية',
    brand_primary_color TEXT DEFAULT '#0B4F6C',
    brand_secondary_color TEXT DEFAULT '#146C8E',
    lab_name_font_size INTEGER DEFAULT 20,
    periodic_report_enabled INTEGER DEFAULT 0,
    periodic_report_frequency TEXT DEFAULT 'monthly',
    periodic_report_last_sent TEXT,
    smtp_host TEXT,
    smtp_port INTEGER,
    smtp_username TEXT,
    smtp_password TEXT,
    smtp_from_email TEXT,
    smtp_to_email TEXT
);


CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    row_id INTEGER,
    action TEXT NOT NULL,
    user_id INTEGER,
    timestamp TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    check_in TEXT NOT NULL,
    check_out TEXT
);

CREATE TABLE IF NOT EXISTS qc_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parameter_id INTEGER NOT NULL REFERENCES test_parameters(id),
    control_level TEXT NOT NULL,
    target_mean REAL NOT NULL,
    target_sd REAL NOT NULL,
    UNIQUE(parameter_id, control_level)
);

CREATE TABLE IF NOT EXISTS qc_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parameter_id INTEGER NOT NULL REFERENCES test_parameters(id),
    control_level TEXT NOT NULL,
    measured_value REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id)
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_visits_patient ON visits(patient_id);
CREATE INDEX IF NOT EXISTS idx_result_values_visit_test ON result_values(visit_test_order_id);
CREATE INDEX IF NOT EXISTS idx_visits_visit_date ON visits(visit_date);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_tests_name ON tests(name);
CREATE INDEX IF NOT EXISTS idx_price_list_test ON price_list_items(test_id);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(patients)").fetchall()]
        if "created_by_user_id" not in columns:
            conn.execute("ALTER TABLE patients ADD COLUMN created_by_user_id INTEGER REFERENCES users(id)")

        order_cols = [r["name"] for r in conn.execute("PRAGMA table_info(visit_test_orders)").fetchall()]
        if "specimen_status" not in order_cols:
            conn.execute("ALTER TABLE visit_test_orders ADD COLUMN specimen_status TEXT NOT NULL DEFAULT 'NotCollected'")

        lab_cols = [r["name"] for r in conn.execute("PRAGMA table_info(lab_settings)").fetchall()]
        if "digital_seal_text" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN digital_seal_text TEXT DEFAULT '🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً.'")
        if "app_title" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN app_title TEXT DEFAULT 'LapLIS - نظام إدارة معمل التحاليل الطبية'")
        if "brand_primary_color" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN brand_primary_color TEXT DEFAULT '#0B4F6C'")
        if "brand_secondary_color" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN brand_secondary_color TEXT DEFAULT '#146C8E'")
        if "supervising_doctor_name" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN supervising_doctor_name TEXT")
            # One-time helpful correction for an existing install: the lab name and doctor name
            # used to be combined into one field (e.g. "معمل نخبة للدكتور مصطفى الزناتي"). Split
            # them automatically so the lab owner doesn't have to retype anything after upgrading -
            # if the pattern isn't recognized, the field is just left blank for them to fill in.
            row = conn.execute("SELECT lab_name FROM lab_settings WHERE id = 1").fetchone()
            if row and row["lab_name"] and "للدكتور" in row["lab_name"]:
                lab_part, _, doctor_part = row["lab_name"].partition("للدكتور")
                lab_part = lab_part.strip()
                doctor_part = doctor_part.strip()
                if lab_part and doctor_part:
                    conn.execute(
                        "UPDATE lab_settings SET lab_name = ?, supervising_doctor_name = ? WHERE id = 1",
                        (lab_part, f"د. {doctor_part}"),
                    )
        if "lab_name_font_size" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN lab_name_font_size INTEGER DEFAULT 20")
        if "periodic_report_enabled" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN periodic_report_enabled INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN periodic_report_frequency TEXT DEFAULT 'monthly'")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN periodic_report_last_sent TEXT")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN smtp_host TEXT")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN smtp_port INTEGER")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN smtp_username TEXT")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN smtp_password TEXT")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN smtp_from_email TEXT")
            conn.execute("ALTER TABLE lab_settings ADD COLUMN smtp_to_email TEXT")

        conn.commit()
    finally:
        conn.close()

