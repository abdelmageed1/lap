"""Application paths: where the SQLite database, invoices and lab reports live on disk."""
import os
import sys


def _app_data_root() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    else:
        base = os.path.expanduser("~/.config")
    return os.path.join(base, "LapLIS-Python")


DATA_DIR = _app_data_root()
DATABASE_PATH = os.path.join(DATA_DIR, "laplis.db")
INVOICES_DIR = os.path.join(DATA_DIR, "Invoices")
REPORTS_DIR = os.path.join(DATA_DIR, "Reports")

# Backups live under the user's Documents folder (not the hidden AppData/config folder) precisely
# so a non-technical user can actually find them without being told where to look.
BACKUPS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "LapLIS-Backups")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(INVOICES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

SEED_DATA_DIR = os.path.join(os.path.dirname(__file__), "seed_data")
