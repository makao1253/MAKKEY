"""Wspólne komponenty interfejsu: karty, kropka stanu, przełącznik motywu,
pole przechwytujące skrót klawiszowy.

Te same klasy (i ten sam wygląd) ma MAKMOUSE - obie aplikacje mają sprawiać
wrażenie jednego programu.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QSlider, QVBoxLayout,
    QWidget,
)

from .. import theme as T
from ..i18n import tr


# --------------------------------------------------------------------------- #
class Card(QFrame):
    """Panel z tytułem i pionową zawartością."""

    def __init__(self, title: str = "", parent: QWidget | None = None,
                 flat: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("CardFlat" if flat else "Card")
        self._outer = QVBoxLayout(self)
        # Ciasne marginesy: cała zawartość zakładek ma się mieścić także na
        # mniejszym ekranie, bez przewijania i bez zmiany skali Windows.
        self._outer.setContentsMargins(11, 8, 11, 9)
        self._outer.setSpacing(6)
        self.title_label: QLabel | None = None
        if title:
            self.title_label = QLabel(title.upper())
            self.title_label.setObjectName("CardTitle")
            self._outer.addWidget(self.title_label)
        self.body = QVBoxLayout()
        self.body.setSpacing(6)
        self._outer.addLayout(self.body)

    def add(self, widget: QWidget) -> QWidget:
        self.body.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self.body.addLayout(layout)

    def set_title(self, text: str) -> None:
        if self.title_label is not None:
            self.title_label.setText(text.upper())


def hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Hint")
    lbl.setWordWrap(True)
    return lbl


def combo(chars: int = 9) -> QComboBox:
    """Lista rozwijana, która nie rozpycha okna do najdłuższej pozycji.

    Domyślna podpowiedź rozmiaru QComboBox to szerokość najdłuższego wpisu -
    przy kilku listach w rzędzie wymusza poziomy pasek przewijania na mniejszym
    ekranie. Pełny tekst i tak widać po rozwinięciu.
    """
    box = QComboBox()
    box.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    box.setMinimumContentsLength(chars)
    return box


def row(*widgets: QWidget, spacing: int = 8, stretch_last: bool = False) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for i, wdg in enumerate(widgets):
        lay.addWidget(wdg, 1 if (stretch_last and i == len(widgets) - 1) else 0)
    return lay


def label_row(text: str, widget: QWidget, width: int = 96) -> QHBoxLayout:
    """Etykieta o stałej szerokości + pole - kolumny w kartach się zgadzają."""
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lbl = QLabel(text)
    lbl.setMinimumWidth(width)
    lay.addWidget(lbl)
    lay.addWidget(widget, 1)
    return lay


# --------------------------------------------------------------------------- #
class StatusPill(QLabel):
    """Kropka + tekst, np. 'Urządzenie podłączone'."""

    def __init__(self, text: str = "", color: str = "", parent: QWidget | None = None,
                 dot: float = 8.0) -> None:
        super().__init__(parent)
        self._color = color or T.TEXT_DIM
        self._dot = dot
        self.setText(text)
        self.setContentsMargins(int(dot + 10), 0, 0, 0)

    def set_state(self, text: str, color: str) -> None:
        self._color = color
        self.setText(text)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        d = self._dot
        if d >= 12:  # większa kropka dostaje delikatną poświatę
            halo = QColor(self._color)
            halo.setAlpha(60)
            p.setBrush(halo)
            p.drawEllipse(QRectF(-1, self.height() / 2 - d / 2 - 3, d + 6, d + 6))
        p.setBrush(QColor(self._color))
        p.drawEllipse(QRectF(2, self.height() / 2 - d / 2, d, d))
        p.end()
        super().paintEvent(event)


class SliderRow(QWidget):
    """Etykieta + suwak + wartość liczbowa."""

    valueChanged = Signal(int)

    def __init__(self, label: str, value: int, lo: int, hi: int,
                 suffix: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._suffix = suffix
        self._name = QLabel(label)
        self._name.setMinimumWidth(120)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(lo, hi)
        self._slider.setValue(max(lo, min(hi, value)))
        self._value = QLabel()
        self._value.setMinimumWidth(48)
        self._value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        lay.addWidget(self._name)
        lay.addWidget(self._slider, 1)
        lay.addWidget(self._value)

        self._slider.valueChanged.connect(self._on_change)
        self._refresh()

    def _on_change(self, _raw: int) -> None:
        self._refresh()
        self.valueChanged.emit(self.value())

    def _refresh(self) -> None:
        self._value.setText(f"{self.value()}{self._suffix}")

    def value(self) -> int:
        return int(self._slider.value())

    def setValue(self, value: int) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(int(value))
        self._slider.blockSignals(False)
        self._refresh()


class ThemeSwitch(QWidget):
    """Dwupozycyjny przełącznik motywu: słońce = jasny, księżyc = ciemny."""

    modeChanged = Signal(str)

    def __init__(self, mode: str = "dark", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = "light" if mode == "light" else "dark"
        self.setFixedSize(74, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tr("Motyw jasny / ciemny"))

    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        mode = "light" if mode == "light" else "dark"
        if mode != self._mode:
            self._mode = mode
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        self._mode = "light" if self._mode == "dark" else "dark"
        self.update()
        self.modeChanged.emit(self._mode)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        light = self._mode == "light"

        p.setPen(QPen(QColor(T.BORDER), 1))
        p.setBrush(QColor(T.FIELD))
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        # Suwak stoi po stronie wybranego motywu.
        cx = r if light else w - r
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T.ACCENT))
        p.drawEllipse(QPointF(cx, h / 2), r - 3, r - 3)

        on, off = QColor("#FFFFFF"), QColor(T.TEXT_DIM)
        self._sun(p, QPointF(r, h / 2), r * 0.52, on if light else off)
        self._moon(p, QPointF(w - r, h / 2), r * 0.52, off if light else on)

    @staticmethod
    def _sun(p: QPainter, c: QPointF, r: float, color: QColor) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(c, r * 0.52, r * 0.52)
        p.setPen(QPen(color, max(1.2, r * 0.24), Qt.SolidLine, Qt.RoundCap))
        for i in range(8):
            a = math.pi * i / 4
            p.drawLine(
                QPointF(c.x() + math.cos(a) * r * 0.82, c.y() + math.sin(a) * r * 0.82),
                QPointF(c.x() + math.cos(a) * r * 1.15, c.y() + math.sin(a) * r * 1.15),
            )

    @staticmethod
    def _moon(p: QPainter, c: QPointF, r: float, color: QColor) -> None:
        full = QPainterPath()
        full.addEllipse(c, r, r)
        bite = QPainterPath()
        bite.addEllipse(QPointF(c.x() + r * 0.58, c.y() - r * 0.30), r * 0.92, r * 0.92)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(full.subtracted(bite))


# --------------------------------------------------------------------------- #
_QT_KEYS = {
    Qt.Key_Escape: "Esc", Qt.Key_Tab: "Tab", Qt.Key_Backspace: "Backspace",
    Qt.Key_Return: "Enter", Qt.Key_Enter: "Enter", Qt.Key_Insert: "Insert",
    Qt.Key_Delete: "Delete", Qt.Key_Home: "Home", Qt.Key_End: "End",
    Qt.Key_PageUp: "PgUp", Qt.Key_PageDown: "PgDn", Qt.Key_Left: "Left",
    Qt.Key_Up: "Up", Qt.Key_Right: "Right", Qt.Key_Down: "Down",
    Qt.Key_Space: "Space", Qt.Key_Print: "PrintScreen", Qt.Key_Pause: "Pause",
    Qt.Key_CapsLock: "CapsLock", Qt.Key_NumLock: "NumLock",
    Qt.Key_ScrollLock: "ScrollLock", Qt.Key_Menu: "Apps",
    Qt.Key_Semicolon: ";", Qt.Key_Equal: "=", Qt.Key_Comma: ",", Qt.Key_Minus: "-",
    Qt.Key_Period: ".", Qt.Key_Slash: "/", Qt.Key_QuoteLeft: "`",
    Qt.Key_BracketLeft: "[", Qt.Key_Backslash: "\\", Qt.Key_BracketRight: "]",
    Qt.Key_Apostrophe: "'",
}
for _i in range(1, 25):
    _QT_KEYS[Qt.Key(int(Qt.Key_F1) + _i - 1)] = f"F{_i}"

_NUMPAD = {Qt.Key_Plus: "Num+", Qt.Key_Minus: "Num-", Qt.Key_Asterisk: "Num*",
           Qt.Key_Slash: "Num/", Qt.Key_Period: "Num."}

_MOD_KEYS = {Qt.Key_Control: "Ctrl", Qt.Key_Shift: "Shift", Qt.Key_Alt: "Alt",
             Qt.Key_AltGr: "Alt", Qt.Key_Meta: "Win"}
_MOD_ORDER = ["Ctrl", "Shift", "Alt", "Win"]


def _mod_names(modifiers) -> list[str]:
    names = []
    if modifiers & Qt.ControlModifier:
        names.append("Ctrl")
    if modifiers & Qt.ShiftModifier:
        names.append("Shift")
    if modifiers & Qt.AltModifier:
        names.append("Alt")
    if modifiers & Qt.MetaModifier:
        names.append("Win")
    return names


class HotkeyEdit(QLineEdit):
    """Pole 'kliknij i naciśnij skrót'. Zwraca zapis typu 'Ctrl+Shift+E'.

    Skrótu nie wpisuje się z klawiatury jako tekstu - pole nagrywa faktycznie
    wciśnięte klawisze, więc nie da się zapisać kombinacji, której system nie
    potrafi wysłać. `mods_only=True` pozwala zapisać sam modyfikator.
    """

    hotkeyChanged = Signal(str)
    captureChanged = Signal(bool)

    def __init__(self, value: str = "", parent: QWidget | None = None,
                 mods_only: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("Capture")
        self.setReadOnly(True)
        self._mods_only = mods_only
        self._idle_text = (tr("kliknij i naciśnij klawisze") if mods_only
                           else tr("kliknij i naciśnij skrót"))
        self.setPlaceholderText(self._idle_text)
        self.setText(value)
        self.setCursor(Qt.PointingHandCursor)
        self._recording = False

    def _set_recording(self, value: bool) -> None:
        if value == self._recording:
            return
        self._recording = value
        self.setProperty("recording", "true" if value else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPlaceholderText(tr("naciśnij  (Esc = wyczyść)") if value else self._idle_text)
        self.captureChanged.emit(value)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._set_recording(True)

    def focusOutEvent(self, event) -> None:
        self._set_recording(False)
        super().focusOutEvent(event)

    def event(self, event) -> bool:
        # Tab i Backtab muszą trafić do keyPressEvent, a nie do nawigacji fokusem.
        if event.type() == QEvent.KeyPress and self._recording:
            if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
                self.keyPressEvent(event)
                return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in _MOD_KEYS:
            # Sam modyfikator jest pełnoprawnym zapisem tylko w polach "co trzymać";
            # gdzie indziej czekamy na klawisz główny.
            if not self._mods_only:
                return
            parts = _mod_names(event.modifiers())
            if _MOD_KEYS[key] not in parts:
                parts.append(_MOD_KEYS[key])
            parts.sort(key=_MOD_ORDER.index)
            self.set_hotkey("+".join(parts))
            return
        if key == Qt.Key_Escape:
            self.set_hotkey("")
            return

        mods = event.modifiers()
        parts = _mod_names(mods)

        name = ""
        keypad = bool(mods & Qt.KeypadModifier)
        if keypad and Qt.Key_0 <= key <= Qt.Key_9:
            name = f"Num{key - Qt.Key_0}"
        elif keypad and key in _NUMPAD:
            name = _NUMPAD[key]
        elif key in _QT_KEYS:
            name = _QT_KEYS[key]
        elif Qt.Key_A <= key <= Qt.Key_Z:
            name = chr(key)
        elif Qt.Key_0 <= key <= Qt.Key_9:
            name = chr(key)
        elif key == Qt.Key_Backtab:
            name = "Tab"

        if not name:
            return
        parts.append(name)
        self.set_hotkey("+".join(parts))

    def set_hotkey(self, value: str) -> None:
        if value != self.text():
            self.setText(value)
            self.hotkeyChanged.emit(value)
        elif not value:
            self.hotkeyChanged.emit(value)
