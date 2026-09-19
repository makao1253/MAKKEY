"""Zakładka "Urządzenie" - wykrywanie MAKKEY wśród urządzeń HID.

Aplikacja przyjmuje wyłącznie urządzenie zgodne z deskryptorem MAKKEY
(vendor usage page 0xFF00, usage 0x01, nazwa produktu "MAKKEY"). Tabela
pokazuje wszystko, co system zgłasza jako HID, razem z powodem pominięcia -
bez tego "nie znaleziono urządzenia" nie dałoby się sensownie zdiagnozować.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QAbstractItemView, QScrollArea,
)

from .. import theme as T
from ..constants import (
    DEVICE_PRODUCT_STRING, DEVICE_MANUFACTURER_STRING,
    HID_USAGE_PAGE_VENDOR, HID_USAGE_MAKKEY,
    REPORT_ID_IN, REPORT_ID_OUT, IN_REPORT_SIZE, OUT_REPORT_SIZE,
)
from ..i18n import tr
from .common import Card, hint, row

# tłumaczone przy budowaniu tabeli (tr)
COLUMNS = ["Nazwa produktu", "VID:PID", "Usage page / usage", "Stan"]


class TabDevice(QWidget):
    rescanRequested = Signal()
    pingRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        area = QScrollArea()
        area.setWidgetResizable(True)
        outer.addWidget(area)

        host = QWidget()
        area.setWidget(host)
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        # --- stan urządzenia ---
        status = Card(tr("Urządzenie {name}", name=DEVICE_PRODUCT_STRING))
        self.status_label = QLabel(tr("Szukanie urządzenia..."))
        self.status_label.setObjectName("Big")
        status.add(self.status_label)

        self.detail_label = hint("")
        status.add(self.detail_label)

        self.rescan_btn = QPushButton(tr("Szukaj ponownie"))
        self.rescan_btn.setObjectName("Primary")
        self.rescan_btn.clicked.connect(self.rescanRequested)
        self.ping_btn = QPushButton(tr("Test łączności (PING)"))
        self.ping_btn.clicked.connect(self.pingRequested)
        status.add_layout(row(self.rescan_btn, self.ping_btn))
        lay.addWidget(status)

        # --- lista urządzeń HID ---
        devices = Card(tr("Urządzenia HID widziane przez system"))
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(c) for c in COLUMNS])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setMinimumHeight(170)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        devices.add(self.table)
        devices.add(hint(tr(
            'Przyjmowane jest wyłącznie urządzenie o nazwie "{name}" '
            "z usage page 0x{page:04X} i usage 0x{usage:02X}. Reszta jest pomijana.",
            name=DEVICE_PRODUCT_STRING, page=HID_USAGE_PAGE_VENDOR, usage=HID_USAGE_MAKKEY,
        )))
        lay.addWidget(devices)

        # --- protokół ---
        protocol = Card(tr("Protokół"))
        protocol.add(hint(tr(
            'Producent "{maker}", produkt "{product}". Raport IN (ID 0x{in_id:02X}, '
            "{in_size} B) niesie bitmapę 13 przycisków; raport OUT "
            "(ID 0x{out_id:02X}, {out_size} B) - kolory diod i tekst na wyświetlacz.",
            maker=DEVICE_MANUFACTURER_STRING, product=DEVICE_PRODUCT_STRING,
            in_id=REPORT_ID_IN, in_size=IN_REPORT_SIZE,
            out_id=REPORT_ID_OUT, out_size=OUT_REPORT_SIZE,
        )))
        self.firmware_label = hint(tr("Wersja firmware: nieznana (wyślij PING)."))
        protocol.add(self.firmware_label)
        protocol.add(hint(tr(
            "MCU: STM32G431KBT6. Przyciski podpięte indywidualnie do GPIO, "
            "diody WS2812B sterowane z tego samego układu, OLED po I2C."
        )))
        lay.addWidget(protocol)
        lay.addStretch(1)

    # ------------------------------------------------------------------ API
    def set_device_state(self, connected: bool, name: str, vid_pid: str = "",
                         usage: str = ""):
        color = T.OK if connected else T.BAD
        state = tr("podłączony") if connected else tr("nie znaleziono")
        self.status_label.setText(f"{name or DEVICE_PRODUCT_STRING} - {state}")
        self.status_label.setStyleSheet(f"color: {color};")
        self.ping_btn.setEnabled(connected)
        self.detail_label.setText(
            f"{vid_pid}   usage {usage}" if connected and vid_pid else
            tr("Podłącz urządzenie albo sprawdź, czy firmware zgłasza własny "
               "deskryptor HID (a nie klawiaturę).")
        )

    def set_devices(self, devices):
        """Wypełnia tabelę listą urządzeń HID zwróconą przez warstwę łącza."""
        self.table.setRowCount(len(devices))
        for r, info in enumerate(devices):
            mine = info.is_makkey()
            values = [
                info.product or tr("(bez nazwy)"),
                info.vid_pid,
                info.usage_text,
                "MAKKEY" if mine else tr("pomijane"),
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if mine and c == len(values) - 1:
                    item.setForeground(QColor(T.OK))
                self.table.setItem(r, c, item)

    def set_firmware(self, version: str):
        self.firmware_label.setText(tr("Wersja firmware: {version}", version=version))
