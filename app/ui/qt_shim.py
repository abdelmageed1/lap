import importlib
import sys

def _load_compatible_qt():
    """Load a Qt binding compatible with the application.
    Preference order:
    1. PySide2 (original)
    2. PySide6 (newer but similar API)
    3. PyQt5 (fallback)
    If a binding other than PySide2 is loaded, it is aliased as ``PySide2``
    so that existing ``from PySide2.xxx import ...`` statements keep working.
    """
    for pkg in ("PySide2", "PySide6", "PyQt5"):
        try:
            module = importlib.import_module(pkg)
            if pkg != "PySide2":
                sys.modules["PySide2"] = module
            return module
        except ImportError:
            continue
    raise ImportError("No compatible Qt binding found. Install PySide2, PySide6, or PyQt5.")

# Execute on import so the alias is set before any other Qt imports.
_load_compatible_qt()
