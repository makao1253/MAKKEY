"""Model danych w pamięci (profile + mapowania przycisków).

Trzymanie modelu osobno od widgetów sprawia, że przy scalaniu
MAKKEY + MAKMOUSE wystarczy podmienić warstwę zapisu, a nie przepisywać UI.
Serializacją zajmuje się app/config.py.
"""
from __future__ import annotations

import ntpath
from dataclasses import dataclass, field

from .constants import (
    ACTION_NONE, ACTION_PROFILE, ACTION_MEDIA, DEFAULT_LED_COLOR,
    GRID_BUTTON_COUNT, PROFILE_BUTTON_INDEX, TOTAL_BUTTON_COUNT,
    MAX_MANUAL_PROFILES,
)
from .i18n import tr


@dataclass
class ButtonMapping:
    """Ustawienia pojedynczego przycisku w obrębie jednego profilu.

    `enabled` to włącznik samego predefiniowania: wyłączony przycisk nie
    wywołuje niczego, ale zachowuje akcję i kolor - po ponownym włączeniu
    wszystko wraca bez przepisywania ustawień. Stan jest indywidualny dla
    każdego profilu.
    """
    action_type: str = ACTION_NONE
    value: str = ""
    color: str = DEFAULT_LED_COLOR
    enabled: bool = True

    def describe(self) -> str:
        """Jednolinijkowy opis akcji - do legend i podglądów."""
        if self.action_type == ACTION_PROFILE:
            return tr("zmiana profilu")
        if self.action_type == ACTION_NONE or not self.value:
            return tr("brak akcji")
        if self.action_type == ACTION_MEDIA:
            return tr(self.value)      # zapisana nazwa akcji jest po polsku
        return self.value


def _default_buttons() -> dict[int, ButtonMapping]:
    buttons = {i: ButtonMapping() for i in range(1, GRID_BUTTON_COUNT + 1)}
    buttons[PROFILE_BUTTON_INDEX] = ButtonMapping(
        action_type=ACTION_PROFILE, value="", color="#FFFFFF"
    )
    return buttons


@dataclass
class Profile:
    name: str
    exe: str = ""
    is_default: bool = False
    enabled: bool = True
    in_manual_cycle: bool = False
    oled_text: str = ""
    buttons: dict[int, ButtonMapping] = field(default_factory=_default_buttons)

    def button(self, index: int) -> ButtonMapping:
        return self.buttons[index]

    def exe_names(self) -> set[str]:
        """Programy z pola "Pliki .exe" w postaci porównywalnej (_exe_key)."""
        parts = self.exe.replace(";", ",").split(",")
        return {_exe_key(part) for part in parts if part.strip()}


def _exe_key(name: str) -> str:
    """'C:\\Apps\\Fusion360.EXE', 'fusion360.exe', 'Fusion360' -> 'fusion360'.

    Wielkość liter, ścieżka i końcówka .exe nie mają znaczenia - użytkownik
    wpisuje nazwę z pamięci, a Windows i tak ich nie rozróżnia.
    """
    base = ntpath.basename(name.strip().strip('"')).lower()
    return base[:-4] if base.endswith(".exe") else base


class AppModel:
    """Kontener na profile + bieżący wybór (profil / zaznaczony przycisk)."""

    def __init__(self):
        self.profiles: list[Profile] = _example_profiles()
        self.current_profile_index: int = 0
        self.selected_button: int = 1
        # True  = profil zmieniany ręcznie przyciskiem 13 (cykl max 4 profile)
        # False = profil dobierany automatycznie po nazwie procesu (.exe)
        self.manual_profile_switching: bool = False

    # --- profile ---
    @property
    def current_profile(self) -> Profile:
        return self.profiles[self.current_profile_index]

    def manual_cycle_profiles(self) -> list[Profile]:
        return [p for p in self.profiles if p.in_manual_cycle]

    def manual_cycle_count(self) -> int:
        return len(self.manual_cycle_profiles())

    def can_add_to_manual_cycle(self) -> bool:
        return self.manual_cycle_count() < MAX_MANUAL_PROFILES

    def profile_for_exe(self, exe: str) -> int | None:
        """Indeks profilu dla programu `exe` w trybie automatycznym.

        Pierwszy włączony profil, który ma ten program na liście; gdy żaden
        nie pasuje - profil domyślny (awaryjny dla nieznanych programów).
        """
        key = _exe_key(exe)
        for index, profile in enumerate(self.profiles):
            if profile.enabled and key in profile.exe_names():
                return index
        for index, profile in enumerate(self.profiles):
            if profile.is_default:
                return index
        return None

    # --- przyciski ---
    def mapping(self, index: int) -> ButtonMapping:
        return self.current_profile.button(index)

    def colors(self) -> dict[int, str]:
        return {i: self.current_profile.buttons[i].color
                for i in range(1, TOTAL_BUTTON_COUNT + 1)}

    def enabled_flags(self) -> dict[int, bool]:
        """Stan predefiniowania każdego przycisku w bieżącym profilu."""
        return {i: self.current_profile.buttons[i].enabled
                for i in range(1, TOTAL_BUTTON_COUNT + 1)}


def _example_profiles() -> list[Profile]:
    """Dane przykładowe, żeby szkielet dało się obejrzeć i klikać."""
    fusion = Profile(name="Fusion 360", exe="Fusion360.exe, Fusion.exe",
                     is_default=True, in_manual_cycle=True, oled_text="FUSION 360")
    kicad = Profile(name="KiCad", exe="kicad.exe, pcbnew.exe, eeschema.exe",
                    in_manual_cycle=True, oled_text="KICAD")
    blender = Profile(name="Blender", exe="blender.exe", oled_text="BLENDER")
    general = Profile(name="Ogólny", exe="", in_manual_cycle=True, oled_text="OGOLNY")

    from .constants import ACTION_SHORTCUT
    demo = {1: ("Ctrl+Z", "#2F80ED"), 2: ("Ctrl+Y", "#2F80ED"),
            3: ("Ctrl+S", "#27AE60"), 4: ("Esc", "#EB5757"),
            5: ("Ctrl+C", "#F2C94C"), 6: ("Ctrl+V", "#F2C94C")}
    for idx, (value, color) in demo.items():
        fusion.buttons[idx] = ButtonMapping(ACTION_SHORTCUT, value, color)

    return [fusion, kicad, blender, general]
