"""Application paths: where the SQLite database, invoices and lab reports live on disk.

All output directories (PDFs, Exports, Backups) are derived from a single configurable
storage root.  The admin can change the root from the Settings screen; the new path is
persisted in storage_config.json inside the hidden AppData folder so it survives upgrades.
"""
import json
import os
import sys


# ---------------------------------------------------------------------------
# Internal AppData folder (hidden; never changed)
# ---------------------------------------------------------------------------

def _app_data_root() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    else:
        base = os.path.expanduser("~/.config")
    return os.path.join(base, "LapLIS-Python")


DATA_DIR = _app_data_root()
DATABASE_PATH = os.path.join(DATA_DIR, "laplis.db")
SEED_DATA_DIR = os.path.join(os.path.dirname(__file__), "seed_data")

_STORAGE_CONFIG_PATH = os.path.join(DATA_DIR, "storage_config.json")

os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Storage root – configurable by Admin
# ---------------------------------------------------------------------------

_DEFAULT_STORAGE_ROOT = os.path.join(os.path.expanduser("~"), "Documents", "LapLIS")


def get_storage_root() -> str:
    """Return the current user-configured storage root directory."""
    try:
        if os.path.isfile(_STORAGE_CONFIG_PATH):
            with open(_STORAGE_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                root = cfg.get("storage_root", "").strip()
                if root:
                    return root
    except Exception:
        pass
    return _DEFAULT_STORAGE_ROOT


def set_storage_root(path: str) -> None:
    """Persist a new storage root and recreate all required sub-directories."""
    path = path.strip()
    try:
        with open(_STORAGE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"storage_root": path}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    _ensure_storage_dirs(path)


def _ensure_storage_dirs(root: str = None) -> None:
    """Create all expected sub-directories under *root* (or current root)."""
    root = root or get_storage_root()
    for sub in [
        get_pdf_reports_dir(root),
        get_pdf_invoices_dir(root),
        get_exports_patients_dir(root),
        get_exports_catalog_dir(root),
        get_backups_dir(root),
    ]:
        os.makedirs(sub, exist_ok=True)


# ---------------------------------------------------------------------------
# Public path accessors  (each accepts an optional explicit root override)
# ---------------------------------------------------------------------------

def get_pdf_reports_dir(root: str = None) -> str:
    return os.path.join(root or get_storage_root(), "PDFs", "Reports")


def get_pdf_invoices_dir(root: str = None) -> str:
    return os.path.join(root or get_storage_root(), "PDFs", "Invoices")


def get_exports_patients_dir(root: str = None) -> str:
    return os.path.join(root or get_storage_root(), "Exports", "Patients")


def get_exports_catalog_dir(root: str = None) -> str:
    return os.path.join(root or get_storage_root(), "Exports", "Catalog")


def get_backups_dir(root: str = None) -> str:
    return os.path.join(root or get_storage_root(), "Backups")


# Legacy aliases (kept for backward compatibility in backup_service.py)
BACKUPS_DIR = get_backups_dir()
INVOICES_DIR = get_pdf_invoices_dir()
REPORTS_DIR = get_pdf_reports_dir()

# Ensure all dirs exist on startup
_ensure_storage_dirs()


# ---------------------------------------------------------------------------
# Logo helpers
# ---------------------------------------------------------------------------

def get_resource_path(relative_path: str) -> str:
    """Resolve path for resources bundled via PyInstaller sys._MEIPASS or normal source execution."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return os.path.join(base_path, relative_path)


def get_logo_path() -> str:
    """Return absolute path to application logo SVG."""
    primary = get_resource_path(os.path.join("logo", "log_lap.svg"))
    if os.path.exists(primary):
        return primary
    color = get_resource_path(os.path.join("logo", "logo_lap_color.svg"))
    if os.path.exists(color):
        return color
    return ""


def get_logo_png_path() -> str:
    """Return path to a cached PNG version of the logo suitable for ReportLab PDF rendering."""
    svg_path = get_logo_path()
    if not svg_path:
        return ""
    png_path = os.path.join(DATA_DIR, "logo_cached.png")
    if not os.path.exists(png_path) or os.path.getmtime(svg_path) > os.path.getmtime(png_path):
        try:
            from PySide2.QtWidgets import QApplication
            from PySide2.QtGui import QPixmap
            # QPixmap aborts the whole process (a Qt qFatal, not a catchable Python exception) if
            # constructed before any QGuiApplication exists - checking for one first, rather than
            # relying on the try/except below, is the only way to actually avoid that crash. This
            # matters beyond just tests: any future script/CLI path that generates a report without
            # first starting the GUI would hit the exact same hard crash.
            if QApplication.instance() is not None:
                pix = QPixmap(svg_path)
                if not pix.isNull():
                    pix.scaledToWidth(300).save(png_path, "PNG")
                    return png_path
        except Exception:
            pass
    return png_path if os.path.exists(png_path) else svg_path


