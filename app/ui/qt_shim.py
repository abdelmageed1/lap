"""Qt compatibility shim – enforces PySide2-only to guarantee Windows 7 support.

PySide6 (Qt 6) dropped Windows 7 support entirely.  Silently falling back to
PySide6 would produce a build that works on the developer's machine but crashes
on the lab's Windows 7 workstations.  We therefore refuse to start if PySide2
is not installed, and emit a clear bilingual message so the problem is obvious
at build time rather than at the client site.
"""

try:
    import PySide2  # noqa: F401 – just verifying it is available
except ImportError:
    raise ImportError(
        "\n"
        "========================================================\n"
        "  PySide2 غير مثبَّت على هذا الجهاز.\n"
        "  PySide2 is not installed on this machine.\n"
        "\n"
        "  الرجاء تثبيته بالأمر:\n"
        "  Please install it with:\n"
        "      pip install PySide2\n"
        "\n"
        "  تحذير: لا تستخدم PySide6 أو PyQt5 بديلاً –\n"
        "  Warning:  Do NOT use PySide6 or PyQt5 as a replacement –\n"
        "  PySide6 (Qt 6) does NOT support Windows 7, which is the\n"
        "  target platform for this application.\n"
        "========================================================\n"
    )
