"""Własny wybór koloru diody LED.

Systemowy QColorDialog wygląda obco na tle reszty aplikacji (i pokazuje
masę opcji nieprzydatnych przy WS2812B), więc rysujemy własny panel:
kwadrat nasycenie/jasność + pasek odcienia + pole HEX + presety.

Panel otwiera się jako popup pod próbką koloru i zamyka kliknięciem obok.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
)

from ..constants import LED_PRESET_COLORS
from ..i18n import tr


class SaturationValueSquare(QWidget):
    """Kwadrat wyboru nasycenia (oś X) i jasności (oś Y)."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(232, 148)
        self.setCursor(Qt.CrossCursor)
        self._hue = 0.58
        self._sat = 1.0
        self._val = 1.0

    def set_hsv(self, hue: float, sat: float, val: float):
        self._hue, self._sat, self._val = hue, sat, val
        self.update()

    def set_hue(self, hue: float):
        self._hue = hue
        self.update()
        self.changed.emit()

    def hsv(self) -> tuple[float, float, float]:
        return self._hue, self._sat, self._val

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # czysty odcień jako podkład
        p.setPen(Qt.NoPen)
        p.setBrush(QColor.fromHsvF(self._hue, 1.0, 1.0))
        p.drawRoundedRect(rect, 6, 6)

        # nasycenie: biel po lewej -> przezroczystość po prawej
        sat_grad = QLinearGradient(rect.topLeft(), rect.topRight())
        sat_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        sat_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(sat_grad)
        p.drawRoundedRect(rect, 6, 6)

        # jasność: przezroczystość u góry -> czerń na dole
        val_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        val_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        val_grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        p.setBrush(val_grad)
        p.drawRoundedRect(rect, 6, 6)

        # znacznik bieżącego koloru
        x = rect.left() + self._sat * rect.width()
        y = rect.top() + (1.0 - self._val) * rect.height()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 160), 3))
        p.drawEllipse(QPointF(x, y), 7, 7)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawEllipse(QPointF(x, y), 7, 7)

    def _update_from_pos(self, pos: QPointF):
        w, h = self.width(), self.height()
        self._sat = min(1.0, max(0.0, pos.x() / w))
        self._val = min(1.0, max(0.0, 1.0 - pos.y() / h))
        self.update()
        self.changed.emit()

    def mousePressEvent(self, event):
        self._update_from_pos(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_from_pos(event.position())


class HueSlider(QWidget):
    """Poziomy pasek odcienia."""

    hueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(232, 18)
        self.setCursor(Qt.PointingHandCursor)
        self._hue = 0.58

    def set_hue(self, hue: float):
        self._hue = hue
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        for i in range(7):
            stop = i / 6.0
            grad.setColorAt(stop, QColor.fromHsvF(stop if stop < 1.0 else 0.999, 1.0, 1.0))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        # uchwyt
        x = rect.left() + self._hue * rect.width()
        p.setBrush(QColor.fromHsvF(self._hue, 1.0, 1.0))
        p.setPen(QPen(QColor(255, 255, 255), 2.5))
        p.drawEllipse(QPointF(x, rect.center().y()), 7.5, 7.5)

    def _update_from_pos(self, pos: QPointF):
        self._hue = min(0.999, max(0.0, pos.x() / self.width()))
        self.update()
        self.hueChanged.emit(self._hue)

    def mousePressEvent(self, event):
        self._update_from_pos(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_from_pos(event.position())


class PresetDot(QPushButton):
    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color_hex)
        self.setStyleSheet(
            f"background:{color_hex}; border-radius:12px;"
            f"border:1px solid rgba(128,128,128,90);"
        )


class ColorPickerPopup(QFrame):
    """Popup z pełnym wyborem koloru. Emituje kolor na bieżąco (podgląd
    na macropadzie zmienia się w trakcie przeciągania)."""

    colorChanged = Signal(str)

    def __init__(self, initial: str, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("ColorPickerPopup")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.square = SaturationValueSquare()
        layout.addWidget(self.square)

        self.hue_slider = HueSlider()
        layout.addWidget(self.hue_slider)

        # --- podgląd + HEX + RGB ---
        row = QHBoxLayout()
        row.setSpacing(10)

        self.preview = QLabel()
        self.preview.setFixedSize(42, 42)
        row.addWidget(self.preview)

        fields = QVBoxLayout()
        fields.setSpacing(4)
        self.hex_edit = QLineEdit()
        self.hex_edit.setMaxLength(7)
        self.hex_edit.setFixedWidth(90)
        fields.addWidget(self.hex_edit)
        self.rgb_label = QLabel()
        self.rgb_label.setObjectName("Hint")
        fields.addWidget(self.rgb_label)
        row.addLayout(fields)
        row.addStretch(1)
        layout.addLayout(row)

        # --- presety ---
        presets_label = QLabel(tr("Szybki wybór").upper())
        presets_label.setObjectName("CardTitle")
        layout.addWidget(presets_label)

        presets = QHBoxLayout()
        presets.setSpacing(6)
        for color_hex in LED_PRESET_COLORS:
            dot = PresetDot(color_hex)
            dot.clicked.connect(lambda _=False, c=color_hex: self.set_color(c))
            presets.addWidget(dot)
        presets.addStretch(1)
        layout.addLayout(presets)

        self.square.changed.connect(self._on_square_changed)
        self.hue_slider.hueChanged.connect(self._on_hue_changed)
        self.hex_edit.editingFinished.connect(self._on_hex_edited)

        self.set_color(initial)

    # ------------------------------------------------------------------ API
    def current_color(self) -> QColor:
        h, s, v = self.square.hsv()
        return QColor.fromHsvF(h, s, v)

    def set_color(self, value: str, emit: bool = True):
        color = QColor(value)
        if not color.isValid():
            return
        h, s, v, _ = color.getHsvF()
        if h < 0:          # odcienie szarości nie mają zdefiniowanego H
            h = self.square.hsv()[0]
        self.square.set_hsv(h, s, v)
        self.hue_slider.set_hue(h)
        self._refresh(emit=emit)

    # -------------------------------------------------------------- wewnątrz
    def _refresh(self, emit: bool = True):
        color = self.current_color()
        name = color.name().upper()
        self.preview.setStyleSheet(
            f"background:{name}; border-radius:9px;"
            f"border:1px solid rgba(128,128,128,90);"
        )
        if self.hex_edit.text().upper() != name:
            self.hex_edit.setText(name)
        self.rgb_label.setText(f"R {color.red()}  G {color.green()}  B {color.blue()}")
        if emit:
            self.colorChanged.emit(name)

    def _on_square_changed(self):
        self._refresh()

    def _on_hue_changed(self, hue: float):
        self.square.set_hue(hue)

    def _on_hex_edited(self):
        color = QColor(self.hex_edit.text())
        if color.isValid():
            self.set_color(color.name())
        else:
            self._refresh(emit=False)
