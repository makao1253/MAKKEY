"""Zakładka "Ustawienia" - wariant urządzenia, wygląd, skrót awaryjny, plik
konfiguracyjny.

Wariant urządzenia (podświetlenie / wyświetlacz) jest ustawieniem globalnym,
a nie właściwością profilu: opisuje sprzęt, który stoi na biurku. Wyłączenie
którejkolwiek opcji chowa w całym programie sekcje, które bez tego sprzętu
i tak niczego by nie zrobiły.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox,
    QPushButton, QFileDialog, QMessageBox, QScrollArea,
)

from .. import theme as T
from ..config import AppConfig, get_config_path
from ..constants import (
    APP_VERSION, DEFAULT_CONFIG_PATH, OLED_WIDTH_PX, OLED_HEIGHT_PX, UPDATE_REPO_URL,
)
from ..i18n import LANGUAGES, tr
from ..updater import MODE_GIT, MODE_RELEASE
from .common import Card, HotkeyEdit, SliderRow, combo, hint, label_row, row


def _color_icon(code: str, size: int = 14) -> QIcon:
    """Kwadracik koloru na rozwijanej liście kolorów wiodących."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(code))
    p.drawRoundedRect(QRectF(0, 0, size, size), 3, 3)
    p.end()
    return QIcon(pm)


class TabSettings(QWidget):
    configPathChanged = Signal(str)     # nowa ścieżka pliku konfiguracyjnego
    settingsChanged = Signal()          # cokolwiek do zapisania
    hardwareChanged = Signal()          # zmiana wariantu (LED / OLED)
    accentChanged = Signal(str)         # kolor wiodący
    brightnessChanged = Signal(int)
    languageChanged = Signal(str)       # kod języka - okno buduje się od nowa
    updateCheckRequested = Signal()
    updateInstallRequested = Signal()

    def __init__(self, cfg: AppConfig, update_mode: str, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._update_mode = update_mode
        self._loading = True

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

        lay.addWidget(self._build_hardware_card())
        lay.addWidget(self._build_app_card())
        lay.addWidget(self._build_update_card())
        lay.addWidget(self._build_panic_card())
        lay.addWidget(self._build_config_card())
        lay.addStretch(1)

        self.load_from_config()
        self._loading = False

    # ------------------------------------------------------------ budowanie
    def _build_hardware_card(self) -> QWidget:
        card = Card(tr("Wariant urządzenia"))

        self.leds_checkbox = QCheckBox(tr("Klawiatura z podświetleniem LED (WS2812B)"))
        self.leds_checkbox.setToolTip(tr(
            "Wyłączone: znika wybór koloru diod, a podgląd rysuje klawisze\n"
            "bez poświaty. Kolory zapisane w profilach zostają nietknięte."
        ))
        self.leds_checkbox.toggled.connect(self._on_leds)
        card.add(self.leds_checkbox)

        self.brightness = SliderRow(tr("Jasność diod"), 64, 0, 255)
        self.brightness.valueChanged.connect(self._on_brightness)
        card.add(self.brightness)

        self.oled_checkbox = QCheckBox(tr(
            'Klawiatura z wyświetlaczem OLED 0.91" ({w}x{h})',
            w=OLED_WIDTH_PX, h=OLED_HEIGHT_PX,
        ))
        self.oled_checkbox.setToolTip(tr(
            "Wyłączone: znika sekcja wyświetlacza w zakładce \"Przyciski\",\n"
            "a podgląd rysuje urządzenie bez ekranu."
        ))
        self.oled_checkbox.toggled.connect(self._on_oled)
        card.add(self.oled_checkbox)

        card.add(hint(tr(
            "Ustawienie opisuje sprzęt, a nie profil - obowiązuje w całym "
            "programie i zapisuje się razem z konfiguracją."
        )))
        return card

    def _build_app_card(self) -> QWidget:
        card = Card(tr("Aplikacja"))

        self.lang_combo = combo(12)
        for code, name in LANGUAGES:
            self.lang_combo.addItem(name, code)
        self.lang_combo.currentIndexChanged.connect(self._on_language)
        card.add_layout(label_row(tr("Język"), self.lang_combo))

        self.accent_combo = combo(12)
        for name, code in T.ACCENTS:
            self.accent_combo.addItem(_color_icon(code), tr(name), code)
        self.accent_combo.currentIndexChanged.connect(self._on_accent)
        card.add_layout(label_row(tr("Kolor wiodący"), self.accent_combo))

        self.autostart_checkbox = QCheckBox(tr("Uruchamiaj MAKKEY z systemem Windows"))
        self.autostart_checkbox.toggled.connect(self._on_autostart)
        card.add(self.autostart_checkbox)

        self.minimize_checkbox = QCheckBox(tr("Minimalizuj do zasobnika systemowego"))
        self.minimize_checkbox.setToolTip(tr(
            "Włączone: zamknięcie okna (X) chowa program do zasobnika i macropad\n"
            "działa dalej. Wyjście przez \"Zakończ\" w menu ikony w tacce.\n"
            "Wyłączone: zamknięcie okna kończy program."
        ))
        self.minimize_checkbox.toggled.connect(self._on_minimize)
        card.add(self.minimize_checkbox)
        self.minimize_hint = hint("")
        card.add(self.minimize_hint)

        card.add(hint(tr(
            "Tryb przełączania profili (ręczny / automatyczny) ustawia się "
            "przełącznikiem przy akcji przycisku 13 w zakładce \"Przyciski\"."
        )))
        return card

    def _build_update_card(self) -> QWidget:
        card = Card(tr("Aktualizacje"))

        if self._update_mode == MODE_GIT:
            source = tr("kod z repozytorium git - aktualizacja przez git pull")
        elif self._update_mode == MODE_RELEASE:
            source = tr("plik exe - aktualizacja z wydań (Releases) na GitHubie")
        else:
            source = tr("katalog programu nie jest repozytorium git - "
                        "aktualizacja z poziomu programu jest niedostępna")
        card.add(hint(tr("Wersja {version}, źródło: {source}", version=APP_VERSION, source=source)))

        self.check_updates_checkbox = QCheckBox(tr("Sprawdzaj aktualizacje przy starcie"))
        self.check_updates_checkbox.toggled.connect(self._on_check_updates)
        card.add(self.check_updates_checkbox)

        self.update_check_btn = QPushButton(tr("Sprawdź teraz"))
        self.update_check_btn.clicked.connect(self.updateCheckRequested)
        self.update_install_btn = QPushButton(tr("Aktualizuj"))
        self.update_install_btn.setObjectName("Primary")
        self.update_install_btn.setEnabled(False)
        self.update_install_btn.clicked.connect(self.updateInstallRequested)
        repo_btn = QPushButton(tr("Otwórz repozytorium"))
        repo_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(UPDATE_REPO_URL)))
        card.add_layout(row(self.update_check_btn, self.update_install_btn, repo_btn))

        self.update_status = hint("")
        self.update_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card.add(self.update_status)

        available = self._update_mode in (MODE_GIT, MODE_RELEASE)
        self.check_updates_checkbox.setEnabled(available)
        self.update_check_btn.setEnabled(available)
        return card

    def _build_panic_card(self) -> QWidget:
        card = Card(tr("Skrót awaryjny"))
        card.add(hint(tr(
            "Natychmiast wyłącza przechwytywanie/remapowanie MAKKEY, np. gdy "
            "błędnie skonfigurowany skrót zacznie \"zapętlać\" system."
        )))

        self.panic_enabled_checkbox = QCheckBox(tr("Włączony"))
        self.panic_enabled_checkbox.toggled.connect(self._on_panic_enabled)
        self.panic_hotkey_edit = HotkeyEdit()
        self.panic_hotkey_edit.hotkeyChanged.connect(self._on_panic_hotkey)

        panic_row = QHBoxLayout()
        panic_row.setContentsMargins(0, 0, 0, 0)
        panic_row.setSpacing(8)
        panic_row.addWidget(self.panic_enabled_checkbox)
        panic_row.addWidget(self.panic_hotkey_edit, 1)
        card.add_layout(panic_row)
        return card

    def _build_config_card(self) -> QWidget:
        card = Card(tr("Plik konfiguracyjny"))
        self.config_path_edit = QLineEdit(str(get_config_path()))
        self.config_path_edit.setReadOnly(True)
        self.config_path_edit.setObjectName("Mono")
        card.add(self.config_path_edit)

        change_btn = QPushButton(tr("Zmień lokalizację..."))
        change_btn.setObjectName("Primary")
        change_btn.clicked.connect(self._choose_config_path)
        default_btn = QPushButton(tr("Wróć do domyślnej"))
        default_btn.clicked.connect(self._reset_config_path)
        open_btn = QPushButton(tr("Otwórz folder"))
        open_btn.clicked.connect(self._open_config_folder)
        card.add_layout(row(change_btn, default_btn, open_btn))

        card.add(hint(tr(
            "Zmiana lokalizacji zapisuje bieżącą konfigurację w nowym miejscu "
            "i od tej pory MAKKEY będzie z niego korzystał."
        )))
        return card

    # ------------------------------------------------------------------ API
    def load_from_config(self):
        self._loading = True
        self.leds_checkbox.setChecked(self.cfg.has_leds)
        self.oled_checkbox.setChecked(self.cfg.has_oled)
        self.brightness.setValue(self.cfg.led_brightness)
        self.brightness.setEnabled(self.cfg.has_leds)
        self.lang_combo.setCurrentIndex(max(0, self.lang_combo.findData(self.cfg.language)))
        index = self.accent_combo.findData(self.cfg.accent)
        self.accent_combo.setCurrentIndex(max(0, index))
        self.autostart_checkbox.setChecked(self.cfg.autostart)
        self.minimize_checkbox.setChecked(self.cfg.minimize_to_tray)
        self._sync_minimize_hint(self.cfg.minimize_to_tray)
        self.check_updates_checkbox.setChecked(self.cfg.check_updates)
        self.panic_enabled_checkbox.setChecked(self.cfg.panic_hotkey_enabled)
        self.panic_hotkey_edit.setText(self.cfg.panic_hotkey)
        self.panic_hotkey_edit.setEnabled(self.cfg.panic_hotkey_enabled)
        self.config_path_edit.setText(str(get_config_path()))
        self._loading = False

    def set_update_status(self, text: str, can_install: bool = False, busy: bool = False):
        """Wynik sprawdzania / postęp aktualizacji (steruje nim MainWindow)."""
        self.update_status.setText(text)
        self.update_install_btn.setEnabled(can_install and not busy)
        self.update_check_btn.setEnabled(
            not busy and self._update_mode in (MODE_GIT, MODE_RELEASE)
        )

    # ------------------------------------------------------------- zdarzenia
    def _on_check_updates(self, checked: bool):
        if not self._loading:
            self.cfg.check_updates = checked
            self.settingsChanged.emit()

    def _on_language(self, _index: int):
        if self._loading:
            return
        code = str(self.lang_combo.currentData())
        if code != self.cfg.language:
            self.languageChanged.emit(code)

    def _on_leds(self, checked: bool):
        self.brightness.setEnabled(checked)
        if self._loading:
            return
        self.cfg.has_leds = checked
        self.hardwareChanged.emit()
        self.settingsChanged.emit()

    def _on_oled(self, checked: bool):
        if self._loading:
            return
        self.cfg.has_oled = checked
        self.hardwareChanged.emit()
        self.settingsChanged.emit()

    def _on_brightness(self, value: int):
        if self._loading:
            return
        self.cfg.led_brightness = value
        self.brightnessChanged.emit(value)
        self.settingsChanged.emit()

    def _on_accent(self, _index: int):
        if self._loading:
            return
        code = str(self.accent_combo.currentData() or T.DEFAULT_ACCENT)
        if code == self.cfg.accent:
            return
        self.cfg.accent = code
        self.accentChanged.emit(code)
        self.settingsChanged.emit()

    def _on_autostart(self, checked: bool):
        if not self._loading:
            self.cfg.autostart = checked
            self.settingsChanged.emit()

    def _on_minimize(self, checked: bool):
        self._sync_minimize_hint(checked)
        if not self._loading:
            self.cfg.minimize_to_tray = checked
            self.settingsChanged.emit()

    def _sync_minimize_hint(self, checked: bool):
        self.minimize_hint.setText(
            tr("Zamknięcie okna (X) chowa program do zasobnika - wyjście przez "
               "\"Zakończ\" w menu ikony w tacce.")
            if checked else
            tr("Zamknięcie okna (X) kończy program - macropad przestaje być obsługiwany.")
        )

    def _on_panic_enabled(self, checked: bool):
        self.panic_hotkey_edit.setEnabled(checked)
        if not self._loading:
            self.cfg.panic_hotkey_enabled = checked
            self.settingsChanged.emit()

    def _on_panic_hotkey(self, value: str):
        if not self._loading:
            self.cfg.panic_hotkey = value
            self.settingsChanged.emit()

    def _choose_config_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Wybierz plik konfiguracyjny"),
            self.config_path_edit.text(), tr("Plik JSON (*.json)")
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self.config_path_edit.setText(path)
        self.configPathChanged.emit(path)

    def _reset_config_path(self):
        self.config_path_edit.setText(str(DEFAULT_CONFIG_PATH))
        self.configPathChanged.emit(str(DEFAULT_CONFIG_PATH))

    def _open_config_folder(self):
        folder = Path(self.config_path_edit.text()).parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except OSError as exc:
            QMessageBox.warning(self, "MAKKEY",
                                tr("Nie udało się otworzyć folderu:\n{error}", error=exc))
