"""Górny pasek aplikacji: logo, stan urządzenia, info, motyw, "Aktywny"."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMessageBox
)

from .. import theme as T
from ..constants import APP_NAME, APP_VERSION, DEVICE_PRODUCT_STRING
from ..i18n import DEFAULT_LANGUAGE, language, tr
from .common import Card, StatusPill, ThemeSwitch
from .toggle_switch import ToggleSwitch


# Długi tekst HTML trzymamy w całości per język - jako klucz tr() byłby
# kruchy (każda poprawka polskiej wersji gubiłaby tłumaczenie).
HOW_IT_WORKS_TEXT = {
    "pl": """\
<h3>Jak działa MAKKEY?</h3>
<p>Urządzenie MAKKEY ma 13 przycisków: 12 ułożonych w matrycy 4x3 oraz
1 przycisk nad matrycą, zarezerwowany na zmianę profilu.</p>
<p><b>1. Wciśnięcie przycisku</b> jest wysyłane z urządzenia jako surowy
raport HID (własny deskryptor, vendor usage page 0xFF00) - urządzenie
nie udaje klawiatury, więc nic nie wpisuje się w aktywnym oknie.</p>
<p><b>2. MAKKEY odczytuje raport</b> i z bitmapy 13 bitów ustala, który
przycisk został wciśnięty oraz jaki profil jest aktualnie aktywny.</p>
<p><b>3. Na podstawie mapowania</b> zdefiniowanego w zakładce
„Przyciski” dla danego profilu, MAKKEY wysyła do systemu docelowy
skrót klawiszowy (np. Ctrl+Z).</p>
<p><b>Predefiniowanie</b> każdego przycisku można wyłączyć osobno
w każdym profilu - przycisk zachowuje wtedy ustawienia, ale nic nie
wywołuje. Kropka w rogu klawisza na podglądzie pokazuje ten stan:
zielona = działa, czerwona = wyłączony.</p>
<p><b>Profile</b> pozwalają temu samemu przyciskowi wywoływać różne
skróty w różnych programach (np. Fusion 360 vs KiCad). Profil można
zmienić ręcznie przyciskiem 13 albo automatycznie - MAKKEY sam wykryje
uruchomiony program po nazwie pliku .exe.</p>
<p><b>Kolory LED</b> (WS2812B) i <b>nazwa profilu na wyświetlaczu</b>
wysyłane są do urządzenia raportem wyjściowym przy aktywacji profilu.</p>
""",
    "en": """\
<h3>How does MAKKEY work?</h3>
<p>The MAKKEY device has 13 buttons: 12 arranged in a 4x3 grid and
1 button above the grid, reserved for switching profiles.</p>
<p><b>1. A button press</b> is sent by the device as a raw HID report
(custom descriptor, vendor usage page 0xFF00) - the device does not
pretend to be a keyboard, so nothing gets typed into the active window.</p>
<p><b>2. MAKKEY reads the report</b> and uses the 13-bit bitmap to work
out which button was pressed and which profile is currently active.</p>
<p><b>3. Based on the mapping</b> defined in the "Buttons" tab for that
profile, MAKKEY sends the target keyboard shortcut (e.g. Ctrl+Z) to the
system.</p>
<p><b>Remapping</b> of each button can be switched off separately in
every profile - the button keeps its settings but does nothing. The dot
in the corner of the key in the preview shows this state:
green = active, red = disabled.</p>
<p><b>Profiles</b> let the same button trigger different shortcuts in
different programs (e.g. Fusion 360 vs KiCad). The profile can be
switched manually with button 13 or automatically - MAKKEY detects the
running program by its .exe file name.</p>
<p><b>LED colors</b> (WS2812B) and the <b>profile name on the display</b>
are sent to the device in an output report when a profile is activated.</p>
""",
}


class TopBar(QWidget):
    themeChanged = Signal(str)      # "dark" / "light"
    activeToggled = Signal(bool)

    def __init__(self, theme_mode: str = "dark", active: bool = True, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = Card()
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(16)

        # --- logo ---
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand = QLabel(APP_NAME)
        brand.setObjectName("Brand")
        sub = QLabel(f"Macropad Software {APP_VERSION}")
        sub.setObjectName("BrandSub")
        brand_box.addWidget(brand)
        brand_box.addWidget(sub)
        bar.addLayout(brand_box)
        bar.addSpacing(10)

        # --- stan urządzenia ---
        self.pill_device = StatusPill(DEVICE_PRODUCT_STRING, T.WARN, dot=15.0)
        font = self.pill_device.font()
        # pointSizeF() daje -1, gdy arkusz stylów ustawił rozmiar w pikselach -
        # dodawanie do tego wyprodukowałoby nieprawidłowy rozmiar.
        base = font.pointSizeF()
        font.setPointSizeF((base if base > 0 else 9.0) + 1.5)
        font.setBold(True)
        self.pill_device.setFont(font)
        bar.addWidget(self.pill_device)
        bar.addStretch(1)

        # --- info ---
        self.info_btn = QPushButton("i")
        self.info_btn.setObjectName("Info")
        self.info_btn.setFixedSize(30, 30)
        self.info_btn.setToolTip(tr("Jak to działa?"))
        self.info_btn.setCursor(Qt.PointingHandCursor)
        self.info_btn.clicked.connect(self._show_info)
        bar.addWidget(self.info_btn)
        bar.addSpacing(10)

        # --- motyw ---
        self.theme_switch = ThemeSwitch(theme_mode)
        self.theme_switch.modeChanged.connect(self.themeChanged)
        bar.addWidget(self.theme_switch)
        bar.addSpacing(10)

        # --- aktywny ---
        bar.addWidget(QLabel(tr("Aktywny")))
        self.active_switch = ToggleSwitch(checked=active)
        self.active_switch.toggledState.connect(self.activeToggled)
        bar.addWidget(self.active_switch)

        card.add_layout(bar)
        outer.addWidget(card)

        self._connected = False
        self._active = active
        self._name = DEVICE_PRODUCT_STRING

    # ------------------------------------------------------------------ API
    def set_device_connected(self, connected: bool, name: str = ""):
        self._connected = connected
        self._name = name or DEVICE_PRODUCT_STRING
        self.refresh_device_state()

    def set_active(self, active: bool):
        self._active = active
        self.refresh_device_state()

    def refresh_device_state(self):
        """Kolor kropki niesie oba stany naraz: czy urządzenie jest widziane
        i czy MAKKEY w ogóle je obsługuje."""
        if not self._connected:
            color, tip = T.BAD, tr("Nie znaleziono urządzenia")
        elif not self._active:
            color, tip = T.WARN, tr("Urządzenie podłączone, ale MAKKEY jest wstrzymany")
        else:
            color, tip = T.OK, tr("Urządzenie podłączone")
        self.pill_device.set_state(self._name, color)
        self.pill_device.setToolTip(tip)

    def set_theme_mode(self, mode: str):
        self.theme_switch.set_mode(mode)

    def _show_info(self):
        box = QMessageBox(self)
        box.setWindowTitle(tr("{app} - jak to działa", app=APP_NAME))
        box.setTextFormat(Qt.RichText)
        box.setText(HOW_IT_WORKS_TEXT.get(language(), HOW_IT_WORKS_TEXT[DEFAULT_LANGUAGE]))
        box.setIcon(QMessageBox.NoIcon)
        box.exec()
