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
            _app = QApplication.instance()
            pix = QPixmap(svg_path)
            if not pix.isNull():
                pix.scaledToWidth(300).save(png_path, "PNG")
                return png_path
        except Exception:
            pass
    return png_path if os.path.exists(png_path) else svg_path

