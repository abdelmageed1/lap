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
    status TEXT NOT NULL DEFAULT 'Ordered'
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
    tagline TEXT,
    address TEXT,
    phone_numbers TEXT,
    footer_signature1 TEXT,
    footer_signature2 TEXT,
    digital_seal_text TEXT DEFAULT '🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً.',
    app_title TEXT DEFAULT 'LapLIS - نظام إدارة معمل التحاليل الطبية',
    brand_primary_color TEXT DEFAULT '#0B4F6C',
    brand_secondary_color TEXT DEFAULT '#146C8E'
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
        
        lab_cols = [r["name"] for r in conn.execute("PRAGMA table_info(lab_settings)").fetchall()]
        if "digital_seal_text" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN digital_seal_text TEXT DEFAULT '🔒 هذا التقرير مُعتمَد إلكترونيًا وبخاتم الإدارة الرسمي ولا يحتاج توقيعًا يدوياً.'")
        if "app_title" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN app_title TEXT DEFAULT 'LapLIS - نظام إدارة معمل التحاليل الطبية'")
        if "brand_primary_color" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN brand_primary_color TEXT DEFAULT '#0B4F6C'")
        if "brand_secondary_color" not in lab_cols:
            conn.execute("ALTER TABLE lab_settings ADD COLUMN brand_secondary_color TEXT DEFAULT '#146C8E'")
            
        conn.commit()
    finally:
        conn.close()

