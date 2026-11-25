"""Środkowy panel: podgląd urządzenia na żywo.

Zawiera interaktywny widok macropada (MacropadWidget) oraz zwięzłą
informację o tym, co robi aktualnie zaznaczony / wciśnięty przycisk.
"""
from __future__ import annotations

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from .. import theme as T
from ..constants import ACTION_NONE, PROFILE_BUTTON_INDEX
from ..i18n import tr
from ..models import AppModel
from .common import Card, StatusPill, hint
from .macropad import MacropadWidget


class DevicePreviewPanel(QWidget):
    buttonSelected = Signal(int)

    def __init__(self, model: AppModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setFixedWidth(344)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        card = Card(tr("Podgląd na żywo"))

        self.macropad = MacropadWidget()
        self.macropad.set_tooltip_provider(self.model.button_tooltip)
        self.macropad.buttonSelected.connect(self.buttonSelected)
        card.add(self.macropad)

        # --- informacja o wciśniętym przycisku ---
        pressed_box = Card(parent=None, flat=True)
        pressed_row = QHBoxLayout()
        pressed_row.setSpacing(8)
        self.pressed_dot = StatusPill("", T.BORDER, dot=10.0)
        self.pressed_dot.setFixedWidth(16)
        pressed_row.addWidget(self.pressed_dot)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        self.pressed_title = QLabel(tr("Brak wciśniętego przycisku"))
        self.pressed_action = hint(tr("Czekam na sygnał z urządzenia..."))
        text_box.addWidget(self.pressed_title)
        text_box.addWidget(self.pressed_action)
        pressed_row.addLayout(text_box, 1)
        pressed_box.add_layout(pressed_row)
        card.add(pressed_box)

        # --- informacja o zaznaczonym przycisku ---
        self.selected_info = hint("")
        card.add(self.selected_info)

        outer.addWidget(card, 1)

        self._pressed_index: int | None = None
        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_pressed)

        self.refresh()

    # ------------------------------------------------------------------ API
    def refresh(self):
        """Przeładowuje kolory, stany i opisy z bieżącego profilu."""
        self.macropad.set_colors(self.model.colors())
        self.macropad.set_enabled_flags(self.model.enabled_flags())
        self.macropad.set_oled_text(self.model.current_profile.name)
        self.macropad.set_selected(self.model.selected_button)
        self._refresh_selected_info()

    def set_hardware(self, leds: bool, oled: bool):
        self.macropad.set_hardware(leds, oled)
        self._refresh_selected_info()

    def set_active(self, on: bool):
        """Stan przełącznika "Aktywny"."""
        self.macropad.set_active(on)
        if not on:
            self._reset_pressed_card()
            self.pressed_action.setText(tr("MAKKEY wstrzymany - nie odbiera przycisków"))

    def set_selected(self, index: int):
        self.macropad.set_selected(index)
        self._refresh_selected_info()

    def set_color(self, index: int, color: str):
        self.macropad.set_color(index, color)

    def set_button_enabled(self, index: int, enabled: bool):
        self.macropad.set_button_enabled(index, enabled)
        self._refresh_selected_info()

    def set_oled_text(self, text: str):
        self.macropad.set_oled_text(text)

    def show_press(self, index: int, hold_ms: int = 450):
        """Sygnalizuje wciśnięcie przycisku.

        hold_ms = 0 oznacza podświetlenie do momentu puszczenia klawisza
        (realne zdarzenie z urządzenia); wartość dodatnia gasi je po czasie
        (używane przy symulacji z zakładki Monitor).
        """
        self.macropad.press(index, True)
        mapping = self.model.mapping(index)

        self.pressed_dot.set_state("", mapping.color if mapping.enabled else T.BAD)
        if index == PROFILE_BUTTON_INDEX:
            self.pressed_title.setText(tr("Przycisk 13 - zmiana profilu"))
            self.pressed_action.setText(tr("Przełączenie na następny profil w cyklu"))
        else:
            self.pressed_title.setText(tr("Przycisk {n}", n=index))
            self.pressed_action.setText(mapping.describe())
        if not mapping.enabled:
            self.pressed_action.setText(tr(
                "{action}  (predefiniowanie wyłączone)", action=self.pressed_action.text()
            ))
        note = mapping.note()
        if note:
            self.pressed_action.setText(f"{self.pressed_action.text()}\n{note}")

        self._pressed_index = index
        if hold_ms > 0:
            self._clear_timer.start(hold_ms)
        else:
            self._clear_timer.stop()

    def clear_press(self, index: int):
        """Puszczenie klawisza zgłoszone przez urządzenie."""
        self.macropad.press(index, False)
        if self._pressed_index == index:
            self._reset_pressed_card()

    def repaint_dot(self):
        """Kropka trzyma swój kolor, więc po zmianie motywu trzeba go nadać ponownie."""
        if self._pressed_index is None:
            self.pressed_dot.set_state("", T.BORDER)

    # ------------------------------------------------------------- wewnątrz
    def _clear_pressed(self):
        if self._pressed_index is not None:
            self.macropad.press(self._pressed_index, False)
        self._reset_pressed_card()

    def _reset_pressed_card(self):
        self._pressed_index = None
        self.pressed_dot.set_state("", T.BORDER)
        self.pressed_title.setText(tr("Brak wciśniętego przycisku"))
        self.pressed_action.setText(tr("Czekam na sygnał z urządzenia..."))

    def _refresh_selected_info(self):
        index = self.model.selected_button
        mapping = self.model.mapping(index)
        if index == PROFILE_BUTTON_INDEX:
            desc = tr("zmiana profilu")
        elif mapping.action_type == ACTION_NONE or not mapping.value:
            desc = tr("brak przypisanej akcji")
        else:
            desc = f"{tr(mapping.action_type)}: {mapping.describe()}"
        text = tr("Zaznaczony: przycisk {n} - {action}", n=index, action=desc)
        if not mapping.enabled:
            text = tr("{action}  [wyłączony]", action=text)
        note = mapping.note()
        if note:
            text = f"{text}\n{note}"
        self.selected_info.setText(text)
