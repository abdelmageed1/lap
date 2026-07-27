from PySide2.QtWidgets import QPushButton
from PySide2.QtCore import QPropertyAnimation, QEasingCurve, QRect

class AnimatedButton(QPushButton):
    """QPushButton with a simple scale animation on press/release.

    The animation shrinks the button to 95 % of its original size when pressed
    and returns to the original geometry when released. Duration is 150 ms
    (configurable via ``animation_duration``).
    """
    def __init__(self, *args, animation_duration: int = 150, **kwargs):
        super().__init__(*args, **kwargs)
        self._duration = animation_duration
        self._original_geom: QRect | None = None
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(self._duration)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)

    def _on_pressed(self):
        # Store original geometry on first press
        if self._original_geom is None:
            self._original_geom = self.geometry()
        geom = self.geometry()
        shrink_factor = 0.95
        dw = int(geom.width() * (1 - shrink_factor) / 2)
        dh = int(geom.height() * (1 - shrink_factor) / 2)
        target = QRect(geom.x() + dw, geom.y() + dh,
                       int(geom.width() * shrink_factor),
                       int(geom.height() * shrink_factor))
        self._anim.stop()
        self._anim.setStartValue(geom)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_released(self):
        if self._original_geom is None:
            return
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(self._original_geom)
        self._anim.start()
        self._anim.finished.connect(self._reset_original)

    def _reset_original(self):
        self._original_geom = None
        self._anim.finished.disconnect(self._reset_original)
