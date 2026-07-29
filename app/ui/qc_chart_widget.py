"""Levey-Jennings chart: plots a series of QC measurements against the target mean and +/-1/2/3 SD
reference lines, flagging out-of-control and warning points in color."""
from PySide2.QtCore import Qt
from PySide2.QtGui import QBrush, QColor, QFont, QPen
from PySide2.QtWidgets import QWidget


class LeveyJenningsChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.records = []
        self.mean = 0.0
        self.sd = 0.0
        self.setMinimumHeight(260)

    def set_data(self, records: list, mean: float, sd: float):
        self.records = records
        self.mean = mean
        self.sd = sd
        self.update()

    def paintEvent(self, event):
        from app.ui.styles import get_color
        painter = None
        try:
            from PySide2.QtGui import QPainter
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.rect()
            w, h = rect.width(), rect.height()
            margin_left, margin_right, margin_top, margin_bottom = 70, 20, 20, 30

            if self.sd <= 0 or not self.records:
                painter.setPen(QColor(get_color("text_muted")))
                painter.setFont(QFont("Segoe UI", 10))
                painter.drawText(10, 30, "لا توجد بيانات كافية لعرض الرسم البياني بعد.")
                return

            plot_w = w - margin_left - margin_right
            plot_h = h - margin_top - margin_bottom

            top_value = self.mean + 4 * self.sd
            bottom_value = self.mean - 4 * self.sd
            value_range = top_value - bottom_value or 1

            def y_for(value):
                ratio = (value - bottom_value) / value_range
                return margin_top + plot_h - (ratio * plot_h)

            # Reference lines: mean, +-1SD, +-2SD, +-3SD
            levels = [(-3, "#DC2626"), (-2, "#F59E0B"), (-1, "#94A3B8"), (0, "#0F766E"),
                      (1, "#94A3B8"), (2, "#F59E0B"), (3, "#DC2626")]
            painter.setFont(QFont("Segoe UI", 8))
            for n_sd, color_hex in levels:
                y = y_for(self.mean + n_sd * self.sd)
                pen = QPen(QColor(color_hex))
                pen.setStyle(Qt.SolidLine if n_sd == 0 else Qt.DashLine)
                painter.setPen(pen)
                painter.drawLine(margin_left, int(y), w - margin_right, int(y))
                painter.setPen(QColor(get_color("text_muted")))
                label = "Mean" if n_sd == 0 else f"{n_sd:+d}SD"
                painter.drawText(5, int(y) + 4, label)

            if len(self.records) < 2:
                point_spacing = plot_w
            else:
                point_spacing = plot_w / (len(self.records) - 1)

            points = []
            for idx, r in enumerate(self.records):
                x = margin_left + idx * point_spacing
                y = y_for(r["measured_value"])
                points.append((x, y, r["status"]))

            status_colors = {"InControl": "#0F766E", "Warning": "#F59E0B", "OutOfControl": "#DC2626"}

            pen = QPen(QColor(get_color("text_muted")))
            pen.setWidth(1)
            painter.setPen(pen)
            for i in range(len(points) - 1):
                painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1]))

            for x, y, status in points:
                color = QColor(status_colors.get(status, "#0F766E"))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)
        finally:
            if painter is not None:
                painter.end()
