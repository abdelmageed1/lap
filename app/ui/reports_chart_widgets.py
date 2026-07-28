"""Visual charting widgets and graphic indicators for ReportsView in PySide2."""
from PySide2.QtCore import Qt, QRectF
from PySide2.QtGui import QColor, QPainter, QBrush, QPen, QFont
from PySide2.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class KPICardWidget(QFrame):
    """Summary card displaying a KPI metric with icon, value, and stylized gradient background."""
    def __init__(self, title: str, value: str, icon: str, bg_color: str = "#0B4F6C", text_color: str = "#FFFFFF"):
        super().__init__()
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {bg_color};
                border-radius: 10px;
                padding: 12px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 12px; opacity: 0.9; font-weight: bold;")

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet("font-size: 18px; font-weight: bold;")

        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_val)
        layout.addLayout(text_layout)

    def set_value(self, value: str):
        self.lbl_val.setText(value)


class VisualProgressBar(QProgressBar):
    """Styled progress bar for displaying percentages with color coding."""
    def __init__(self, color_hex: str = "#0D9488"):
        super().__init__()
        self.setTextVisible(True)
        self.setRange(0, 100)
        self.setFixedHeight(18)
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #CBD5E1;
                border-radius: 9px;
                text-align: center;
                color: #0F172A;
                font-weight: bold;
                font-size: 10px;
                background-color: #F1F5F9;
            }}
            QProgressBar::chunk {{
                background-color: {color_hex};
                border-radius: 8px;
            }}
        """)


class DistributionBarWidget(QWidget):
    """Multi-segment bar chart representing Paid (Green), Discount (Yellow), and Balance (Red) percentages."""
    def __init__(self, paid: float = 0, discount: float = 0, balance: float = 0):
        super().__init__()
        self.setFixedHeight(20)
        self.set_values(paid, discount, balance)

    def set_values(self, paid: float, discount: float, balance: float):
        total = paid + discount + balance
        if total <= 0:
            self.paid_pct = 0
            self.disc_pct = 0
            self.bal_pct = 0
        else:
            self.paid_pct = (paid / total) * 100
            self.disc_pct = (discount / total) * 100
            self.bal_pct = (balance / total) * 100
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        # Background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#E2E8F0")))
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        if self.paid_pct + self.disc_pct + self.bal_pct <= 0:
            return

        x = 0
        w_paid = (self.paid_pct / 100) * w
        w_disc = (self.disc_pct / 100) * w
        w_bal = (self.bal_pct / 100) * w

        if w_paid > 0:
            painter.setBrush(QBrush(QColor("#10B981")))  # Emerald Green for Paid
            painter.drawRoundedRect(x, 0, w_paid, h, 6, 6)
            x += w_paid

        if w_disc > 0:
            painter.setBrush(QBrush(QColor("#F59E0B")))  # Amber Yellow for Discount
            painter.drawRect(x, 0, w_disc, h)
            x += w_disc

        if w_bal > 0:
            painter.setBrush(QBrush(QColor("#EF4444")))  # Rose Red for Balance
            painter.drawRoundedRect(x, 0, w_bal, h, 6, 6)


class BarChartWidget(QWidget):
    """Custom horizontal bar chart for visual comparisons (Doctors, Departments, Staff)."""
    def __init__(self, title: str = ""):
        super().__init__()
        self.title = title
        self.items = []  # list of tuples: (label, value, formatted_val, color_hex)
        self.setMinimumHeight(220)

    def set_data(self, items: list):
        """items: list of dicts with 'label', 'value', 'display_val', 'color'"""
        self.items = items
        max_v = max([it.get("value", 0) for it in items], default=1)
        self.max_val = max_v if max_v > 0 else 1
        self.setMinimumHeight(max(220, len(items) * 40 + 40))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        w = rect.width()

        # Title
        painter.setPen(QColor("#0F172A"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(10, 20, self.title)

        if not self.items:
            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(10, 60, "لا تتوفر بيانات للعرض خلال الفترة المحددة.")
            return

        y = 45
        bar_height = 22
        max_label_w = 140
        val_w = 80
        chart_w = w - max_label_w - val_w - 30

        for item in self.items:
            lbl = item.get("label", "")
            val = item.get("value", 0)
            disp = item.get("display_val", str(val))
            color = QColor(item.get("color", "#0F766E"))

            # Draw Label (RTL friendly)
            painter.setPen(QColor("#1E293B"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(10, y + 15, lbl[:20])

            # Draw Bar Background
            bar_x = max_label_w
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#F1F5F9")))
            painter.drawRoundedRect(bar_x, y, chart_w, bar_height, 5, 5)

            # Draw Bar Fill
            fill_w = (val / self.max_val) * chart_w if self.max_val > 0 else 0
            if fill_w > 0:
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(bar_x, y, max(fill_w, 8), bar_height, 5, 5)

            # Draw Value Label
            painter.setPen(QColor("#0F172A"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.drawText(bar_x + chart_w + 10, y + 15, disp)

            y += 36
