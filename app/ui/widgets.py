"""Small shared UI building blocks used across screens to keep the app feeling guided and
consistent rather than dropping the user into a bare form with no explanation."""
from PySide2.QtWidgets import QFrame, QHBoxLayout, QLabel


class HintBanner(QFrame):
    """A single friendly line at the top of a screen explaining what it's for and how to use it."""

    def __init__(self, text: str):
        super().__init__()
        self.setObjectName("HintBanner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(10)

        icon = QLabel("ℹ")
        icon.setObjectName("HintIcon")
        layout.addWidget(icon)

        label = QLabel(text)
        label.setObjectName("HintText")
        label.setWordWrap(True)
        layout.addWidget(label, 1)


def wrappable_path(path: str) -> str:
    """Inserts a zero-width space after each path separator so a long absolute file path can wrap
    inside a QLabel instead of forcing the whole layout wider (QLabel word-wrap only breaks at
    existing whitespace, and a path has none)."""
    zwsp = "​"
    return path.replace("\\", "\\" + zwsp).replace("/", "/" + zwsp)


class StepLabel(QLabel):
    """A small numbered-step heading (e.g. "1. بيانات المريض") used to break a long form into an
    obvious sequence instead of one undifferentiated wall of fields."""

    def __init__(self, number: int, text: str):
        super().__init__(f"{number}. {text}")
        self.setObjectName("StepLabel")
