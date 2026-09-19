"""Przełącznik wł/wył ("Aktywny" w pasku górnym, tryb profili).

QCheckBox nie pozwala ładnie namalować suwaka samym QSS, więc rysujemy go
ręcznie. Kolory czytamy z motywu dopiero w trakcie rysowania - dzięki temu
zmiana motywu albo koloru wiodącego działa bez przebudowy widgetu.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Property, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QAbstractButton, QSizePolicy

_WIDTH = 46
_HEIGHT = 24


class ToggleSwitch(QAbstractButton):
    toggledState = Signal(bool)

    def __init__(self, parent=None, checked: bool = True):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # bez sztywnego rozmiaru QAbstractButton rozciąga się na cały layout
        self.setFixedSize(_WIDTH, _HEIGHT)

        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self.toggled.connect(self._animate)
        self.toggled.connect(self.toggledState)

    def _animate(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self) -> QSize:
        return QSize(_WIDTH, _HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(_WIDTH, _HEIGHT)

    def getOffset(self) -> float:
        return self._offset

    def setOffset(self, value: float):
        self._offset = value
        self.update()

    offset = Property(float, getOffset, setOffset)

    def paintEvent(self, _event):
        from .. import theme as T

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        track = self._blend(QColor(T.TOGGLE_OFF), QColor(T.ACCENT), self._offset)

        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        knob_d = rect.height() - 4
        x = rect.x() + 2 + self._offset * (rect.width() - knob_d - 4)
        y = rect.y() + 2
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(int(x), int(y), int(knob_d), int(knob_d))

    @staticmethod
    def _blend(c1: QColor, c2: QColor, t: float) -> QColor:
        return QColor(
            int(c1.red() + (c2.red() - c1.red()) * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue() + (c2.blue() - c1.blue()) * t),
        )
