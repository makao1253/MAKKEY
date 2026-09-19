"""Zakładka "Monitor" - podgląd tego, co przychodzi z urządzenia.

Urządzenie wysyła surowe raporty HID (Report ID 0x01) z bitmapą 13
przycisków. Monitor pokazuje stan każdego przycisku, ostatnie zdarzenie
i strumień komunikatów - dzięki temu widać, czy firmware faktycznie nadaje,
zanim zacznie się szukać błędu w mapowaniach.

Przycisk "Symuluj" pozwala przetestować wizualizację bez podłączonego
urządzenia.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QPlainTextEdit,
    QPushButton, QCheckBox, QSizePolicy,
)

from ..constants import (
    GRID_BUTTON_COUNT, GRID_COLUMNS, PROFILE_BUTTON_INDEX, TOTAL_BUTTON_COUNT,
    DEVICE_PRODUCT_STRING, REPORT_ID_IN,
)
from ..i18n import tr
from .common import Card, hint, row

LOG_LIMIT = 500


class PressIndicator(QFrame):
    """Kafelek jednego przycisku - zapala się przy wciśnięciu."""

    def __init__(self, index: int, caption: str, parent=None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("PressIndicator")
        self.setFixedHeight(38)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(0)

        self.number_label = QLabel(str(index))
        self.number_label.setAlignment(Qt.AlignCenter)
        self.number_label.setStyleSheet("font-size:12px; font-weight:700;")
        layout.addWidget(self.number_label)

        self.caption_label = QLabel(caption)
        self.caption_label.setAlignment(Qt.AlignCenter)
        self.caption_label.setObjectName("Hint")
        layout.addWidget(self.caption_label)

        self._set_active(False)

    def _set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def flash(self, active: bool):
        self._set_active(active)

    def set_caption(self, text: str):
        self.caption_label.setText(text)


class TabMonitor(QWidget):
    simulatePress = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        # --- wciśnięte przyciski ---
        pressed = Card(tr("Wciśnięte przyciski"))
        grid_host = QWidget()
        # bez tego karta jest ściskana poniżej sizeHint i kafelki nachodzą
        # na siebie przy niższych oknach
        grid_host.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        self.indicators: dict[int, PressIndicator] = {}
        for i in range(GRID_BUTTON_COUNT):
            index = i + 1
            indicator = PressIndicator(index, "-")
            self.indicators[index] = indicator
            grid.addWidget(indicator, i // GRID_COLUMNS, i % GRID_COLUMNS)

        profile_indicator = PressIndicator(PROFILE_BUTTON_INDEX, tr("profil"))
        self.indicators[PROFILE_BUTTON_INDEX] = profile_indicator
        grid.addWidget(profile_indicator, GRID_BUTTON_COUNT // GRID_COLUMNS, 0)

        rows = GRID_BUTTON_COUNT // GRID_COLUMNS + 1
        grid_host.setFixedHeight(rows * 38 + (rows - 1) * 6)
        pressed.add(grid_host)
        lay.addWidget(pressed)

        # --- ostatnie zdarzenie ---
        report = Card(tr("Ostatni raport"))
        self.report_hex = QLabel("--")
        self.report_hex.setObjectName("Mono")
        self.report_hex.setTextInteractionFlags(Qt.TextSelectableByMouse)
        report.add(self.report_hex)
        self.report_desc = hint(tr("Brak odebranych danych."))
        report.add(self.report_desc)
        lay.addWidget(report)

        # --- strumień zdarzeń ---
        stream = Card(tr("Strumień zdarzeń"))
        self.event_stream = QPlainTextEdit()
        self.event_stream.setObjectName("Mono")
        self.event_stream.setReadOnly(True)
        self.event_stream.setMaximumBlockCount(LOG_LIMIT)
        self.event_stream.setPlaceholderText(tr(
            "Tu pojawią się raporty z urządzenia {name} po jego podłączeniu...",
            name=DEVICE_PRODUCT_STRING,
        ))
        self.event_stream.setMinimumHeight(110)
        stream.add(self.event_stream)

        clear_btn = QPushButton(tr("Wyczyść"))
        clear_btn.clicked.connect(self.event_stream.clear)
        simulate_btn = QPushButton(tr("Symuluj naciśnięcie"))
        simulate_btn.setObjectName("Primary")
        simulate_btn.setToolTip(tr("Test wizualizacji bez podłączonego urządzenia"))
        simulate_btn.clicked.connect(self._simulate)
        self.raw_checkbox = QCheckBox(tr("Pokazuj surowe raporty"))
        self.raw_checkbox.setChecked(True)
        controls = row(clear_btn, simulate_btn)
        controls.addStretch(1)
        controls.addWidget(self.raw_checkbox)
        stream.add_layout(controls)
        lay.addWidget(stream, 1)

        self._sim_index = 0

    # ------------------------------------------------------------------ API
    def set_captions(self, captions: dict[int, str]):
        """Podpis pod numerem kafelka - akcja przypisana w bieżącym profilu."""
        for index, text in captions.items():
            indicator = self.indicators.get(index)
            if indicator is not None:
                indicator.set_caption(text)

    def log_press(self, index: int, action: str = ""):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.report_hex.setText(tr("ID 0x{id:02X}  przycisk {n}", id=REPORT_ID_IN, n=index))
        self.report_desc.setText(action or tr("brak przypisanej akcji"))
        self.event_stream.appendPlainText(
            f"{stamp}  " + tr("przycisk {n} DÓŁ", n=index)
            + (f"  ->  {action}" if action else "")
        )
        indicator = self.indicators.get(index)
        if indicator:
            indicator.flash(True)

    def clear_press(self, index: int):
        indicator = self.indicators.get(index)
        if indicator:
            indicator.flash(False)

    def append_raw(self, line: str):
        """Surowa linia z warstwy HID (widoczna, gdy włączony podgląd)."""
        if not self.raw_checkbox.isChecked():
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        self.event_stream.appendPlainText(f"{stamp}  {line}")

    def append_note(self, line: str):
        """Komunikat aplikacji (np. błąd wysyłki skrótu) - widoczny zawsze."""
        stamp = datetime.now().strftime("%H:%M:%S")
        self.event_stream.appendPlainText(f"{stamp}  {line}")

    def _simulate(self):
        self._sim_index = self._sim_index % TOTAL_BUTTON_COUNT + 1
        self.simulatePress.emit(self._sim_index)
