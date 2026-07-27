from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout
from PySide2.QtCore import Qt
from app.services import visit_service

class PatientTrackerWidget(QWidget):
    """Widget to visualise the journey of a patient for a selected visit.

    It shows the ordered list of stages from the ``visit_test_orders`` ``status`` column.
    The UI consists of a combo box to pick a recent visit and a vertical list of
    stage labels with colour cues.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تتبّع حالة المريض")
        self.resize(400, 300)
        layout = QVBoxLayout(self)

        # Header controls
        header = QHBoxLayout()
        self.visit_combo = QComboBox()
        self.visit_combo.setToolTip("اختر زيارة لعرض مسار المريض")
        self.load_visits()
        self.visit_combo.currentIndexChanged.connect(self.update_journey)
        header.addWidget(QLabel("زيارة:"))
        header.addWidget(self.visit_combo)
        layout.addLayout(header)

        # Journey container
        self.journey_container = QVBoxLayout()
        layout.addLayout(self.journey_container)

        # Close button
        close_btn = QPushButton("إغلاق")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def load_visits(self):
        """Load a short list of recent visits for quick access.
        Uses ``visit_service.get_todays_visits`` as a simple source.
        """
        self.visits = visit_service.get_todays_visits()
        self.visit_combo.clear()
        for v in self.visits:
            label = f"{v['invoice_number']} - {v['patient_name']} ({v['visit_date'][:16]})"
            self.visit_combo.addItem(label, v['id'])

    def update_journey(self):
        # Clear previous widgets
        for i in reversed(range(self.journey_container.count())):
            widget = self.journey_container.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        visit_id = self.visit_combo.currentData()
        if not visit_id:
            return
        journey = visit_service.get_patient_journey(visit_id)
        if not journey:
            self.journey_container.addWidget(QLabel("لا توجد مراحل مسجلة لهذه الزيارة"))
            return
        # Display each stage with colour based on status
        status_colors = {
            "Ordered": "#2563EB",   # blue
            "Collected": "#10B981",  # green
            "In Progress": "#FBBF24",  # amber
            "Reviewed": "#8B5CF6",   # purple
        }
        for stage in journey:
            status = stage.get('status', 'Ordered')
            color = status_colors.get(status, "#6B7280")
            label = QLabel(f"{stage.get('test_name', '')}: {status}")
            label.setStyleSheet(f"color: {color}; font-weight: 500;")
            self.journey_container.addWidget(label)
