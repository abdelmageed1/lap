from datetime import datetime
from typing import Optional

from app.db import get_connection


def log_action(table_name: str, row_id: Optional[int], action: str, user_id: Optional[int] = None,
                details: Optional[str] = None, conn=None) -> None:
    """Records one audit entry.

    Pass the caller's own open `conn` when logging from inside a function that already holds a
    write transaction on the database (e.g. mid-way through creating a visit) - opening and
    committing a second connection while the first has uncommitted writes makes SQLite block the
    second writer until it hits the lock timeout, which then raises OperationalError. Every caller
    in this codebase wraps log_action in try/except, so without passing `conn` that failure is
    silently swallowed and the audit row is simply never written (this is exactly the bug that was
    found: audit_logs stayed empty even though visits/results were saving correctly).
    """
    owns_connection = conn is None
    if owns_connection:
        conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_logs (table_name, row_id, action, user_id, timestamp, details) VALUES (?, ?, ?, ?, ?, ?)",
            (table_name, row_id, action, user_id, datetime.utcnow().isoformat(), details),
        )
        if owns_connection:
            conn.commit()
    finally:
        if owns_connection:
            conn.close()
