"""Whole-database backup & restore.

A single file copy captures patients, visits, results, and the entire test/pricing catalog
together, since they all live in one SQLite file - so one backup covers both "customer data" and
"test data" at once, with nothing to keep in sync between separate exports."""
import os
import shutil
from datetime import datetime

from app.config import BACKUPS_DIR, DATABASE_PATH


def create_backup() -> str:
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = os.path.join(BACKUPS_DIR, f"laplis-backup-{stamp}.db")
    shutil.copy2(DATABASE_PATH, dest)
    return dest


def list_backups() -> list:
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    files = [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".db") and not f.startswith("pre-restore-")]
    files.sort(reverse=True)
    return [{"name": f, "path": os.path.join(BACKUPS_DIR, f)} for f in files]


def restore_backup(backup_path: str) -> str:
    """Overwrites the live database with a previously-made backup file. Returns the path of a
    safety copy taken of the about-to-be-replaced database, in case of a mistaken restore.

    The app must be closed and reopened afterwards: this only swaps the file on disk, it cannot
    reach into an already-running program's screens and refresh what they've already loaded."""
    if not os.path.isfile(backup_path):
        raise FileNotFoundError(backup_path)
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pre_restore_path = os.path.join(BACKUPS_DIR, f"pre-restore-{stamp}.db")
    if os.path.isfile(DATABASE_PATH):
        shutil.copy2(DATABASE_PATH, pre_restore_path)
    shutil.copy2(backup_path, DATABASE_PATH)
    return pre_restore_path
