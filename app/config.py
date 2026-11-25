"""Zapis i odczyt konfiguracji MAKKEY.

Konfiguracja (ustawienia + profile + mapowania + kolory) trzymana jest
w jednym pliku JSON, którego lokalizację użytkownik może zmienić.
Sama ścieżka do tego pliku musi być gdzieś zapamiętana - służy do tego
mały "wskaźnik" w %APPDATA%/MAKKEY/location.json.

Eksport to zwykły zapis (save) pod inną ścieżką, a import czyta plik
w tym samym formacie - config.json i plik eksportu są wymienne.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, fields as dataclass_fields
from pathlib import Path

from .constants import (
    APP_VERSION, DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_PATH, DEFAULT_PANIC_HOTKEY,
    ACTION_NONE, DEFAULT_LED_COLOR, TOTAL_BUTTON_COUNT, PROFILE_BUTTON_INDEX,
    ACTION_PROFILE, DEFAULT_LED_BRIGHTNESS,
)
from .theme import DEFAULT_ACCENT

LOCATION_FILE = DEFAULT_CONFIG_DIR / "location.json"
CONFIG_VERSION = 2


class ConfigError(Exception):
    """Pliku nie da się wczytać jako konfiguracji MAKKEY.

    `template` + `fields` to nieprzetłumaczony komunikat dla i18n.tr - tak
    samo jak w wyniku load().
    """

    def __init__(self, template: str, **fields):
        super().__init__(template.format(**fields))
        self.template = template
        self.fields = fields


@dataclass
class AppConfig:
    """Ustawienia globalne (nie związane z konkretnym profilem)."""
    active: bool = True
    theme: str = "dark"
    accent: str = DEFAULT_ACCENT
    language: str = "pl"
    autostart: bool = False
    minimize_to_tray: bool = True
    panic_hotkey: str = DEFAULT_PANIC_HOTKEY
    panic_hotkey_enabled: bool = True

    # --- wariant sprzętowy ---
    # Opisuje, co fizycznie ma podłączony macropad. Wyłączenie chowa
    # w całym programie sekcje, które bez tego sprzętu i tak nic nie robią.
    has_leds: bool = True
    has_oled: bool = True
    led_brightness: int = DEFAULT_LED_BRIGHTNESS


# --------------------------------------------------------------- lokalizacja
def get_config_path() -> Path:
    """Aktualna ścieżka pliku konfiguracyjnego (domyślna albo zapisana
    wcześniej przez użytkownika)."""
    try:
        if LOCATION_FILE.is_file():
            data = json.loads(LOCATION_FILE.read_text(encoding="utf-8"))
            stored = data.get("config_path")
            if stored:
                return Path(stored)
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_CONFIG_PATH


def set_config_path(path: Path) -> None:
    """Zapamiętuje nową lokalizację pliku konfiguracyjnego."""
    LOCATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCATION_FILE.write_text(
        json.dumps({"config_path": str(path)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def reset_config_path() -> Path:
    """Wraca do domyślnej lokalizacji (kasuje wskaźnik)."""
    try:
        LOCATION_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    return DEFAULT_CONFIG_PATH


# ------------------------------------------------------------- serializacja
def _profile_to_dict(profile) -> dict:
    return {
        "name": profile.name,
        "exe": profile.exe,
        "is_default": profile.is_default,
        "enabled": profile.enabled,
        "in_manual_cycle": profile.in_manual_cycle,
        "buttons": {
            str(index): {
                "action_type": mapping.action_type,
                "value": mapping.value,
                "color": mapping.color,
                "enabled": mapping.enabled,
                "comment": mapping.comment,
            }
            for index, mapping in sorted(profile.buttons.items())
        },
    }


def _profile_from_dict(data: dict):
    from .models import Profile, ButtonMapping

    # Teksty przez str(): importowany plik mógł być poprawiany ręcznie,
    # a liczba zamiast nazwy wywróciłaby dopiero widgety.
    profile = Profile(
        name=str(data.get("name", "Profil")),
        exe=str(data.get("exe", "")),
        is_default=bool(data.get("is_default", False)),
        enabled=bool(data.get("enabled", True)),
        in_manual_cycle=bool(data.get("in_manual_cycle", False)),
        # "oled_text" z wcześniejszych wersji jest pomijany - wyświetlacz
        # pokazuje zawsze nazwę profilu.
    )
    stored = data.get("buttons")
    if not isinstance(stored, dict):
        stored = {}
    for index in range(1, TOTAL_BUTTON_COUNT + 1):
        raw = stored.get(str(index))
        if not isinstance(raw, dict):
            raw = {}
        default_action = ACTION_PROFILE if index == PROFILE_BUTTON_INDEX else ACTION_NONE
        profile.buttons[index] = ButtonMapping(
            action_type=str(raw.get("action_type", default_action)),
            value=str(raw.get("value", "")),
            color=str(raw.get("color", DEFAULT_LED_COLOR)),
            # Pliki z wersji 1 nie znały tego pola - tam każdy przycisk działał.
            enabled=bool(raw.get("enabled", True)),
            # Starsze pliki nie znały komentarzy - przycisk zostaje bez opisu.
            comment=str(raw.get("comment", "")),
        )
    return profile


def save(cfg: AppConfig, model, path: Path | None = None) -> Path:
    """Zapisuje całość do JSON. Zwraca ścieżkę, pod którą zapisano.

    Służy też do eksportu - wtedy `path` wskazuje plik wybrany przez
    użytkownika, a wskaźnik lokalizacji zostaje nietknięty.
    """
    target = Path(path) if path else get_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": CONFIG_VERSION,
        "app_version": APP_VERSION,         # program, który zapisał plik
        "settings": asdict(cfg),
        "manual_profile_switching": model.manual_profile_switching,
        "current_profile_index": model.current_profile_index,
        "profiles": [_profile_to_dict(p) for p in model.profiles],
    }
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return target


def load(cfg: AppConfig, model,
         path: Path | None = None) -> tuple[bool, str, dict]:
    """Wczytuje konfigurację w miejscu (mutuje `cfg` i `model`).

    Zwraca (czy_wczytano, komunikat, pola_komunikatu). Komunikat jest
    nieprzetłumaczonym szablonem dla i18n.tr - język zapisany jest dopiero
    w tej konfiguracji, więc tłumaczy go wywołujący, gdy już go ustawi.
    """
    source = Path(path) if path else get_config_path()
    if not source.is_file():
        return False, "Nie znaleziono {path} - użyto ustawień domyślnych.", {"path": source}

    try:
        _apply_payload(cfg, model, _read_payload(source))
    except ConfigError as exc:
        return False, exc.template, exc.fields
    return True, "Wczytano konfigurację z {path}", {"path": source}


def import_config(path: Path) -> tuple[AppConfig, object]:
    """Wczytuje plik (np. wcześniejszy eksport) do NOWYCH obiektów.

    Bieżąca konfiguracja zostaje nietknięta, dopóki cały plik nie okaże się
    poprawny - podmianę robi wywołujący. Zwraca (AppConfig, AppModel),
    przy błędzie rzuca ConfigError.
    """
    from .models import AppModel

    source = Path(path)
    payload = _read_payload(source)
    cfg, model = AppConfig(), AppModel()
    try:
        _apply_payload(cfg, model, payload)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ConfigError("Plik {path} ma nieprawidłową zawartość: {error}",
                          path=source, error=exc) from exc
    return cfg, model


def _read_payload(source: Path) -> dict:
    """Treść pliku konfiguracyjnego jako słownik. Rzuca ConfigError."""
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:      # ValueError: zły JSON / kodowanie
        raise ConfigError("Nie udało się wczytać {path}: {error}",
                          path=source, error=exc) from exc
    # Każdy zapis MAKKEY ma obie sekcje - po nich poznajemy, że to nie jest
    # przypadkowy plik JSON.
    if not isinstance(payload, dict) or not ("settings" in payload or "profiles" in payload):
        raise ConfigError("Plik {path} nie jest konfiguracją MAKKEY.", path=source)
    return payload


def _apply_payload(cfg: AppConfig, model, payload: dict) -> None:
    """Przepisuje treść pliku do `cfg` i `model` (w miejscu)."""
    settings = payload.get("settings")
    settings = dict(settings) if isinstance(settings, dict) else {}
    # Wersja 1 trzymała motyw jako flagę logiczną, a tryb testowy klawiatury
    # zniknął razem z przejściem urządzenia na własny deskryptor HID. Wybór
    # źródła tekstu OLED odpadł - wyświetlacz pokazuje zawsze nazwę profilu.
    if "dark_theme" in settings and "theme" not in settings:
        settings["theme"] = "dark" if settings["dark_theme"] else "light"
    settings.pop("dark_theme", None)
    settings.pop("accept_any_keyboard", None)
    settings.pop("oled_source", None)

    known = {f.name for f in dataclass_fields(cfg)}
    for key, value in settings.items():
        # Wartość innego typu niż domyślna (np. tekst zamiast liczby w ręcznie
        # poprawianym pliku) jest pomijana - zostaje ustawienie domyślne.
        if key in known and isinstance(value, type(getattr(cfg, key))):
            setattr(cfg, key, value)

    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list):
        raw_profiles = []
    profiles = [_profile_from_dict(d) for d in raw_profiles if isinstance(d, dict)]
    if profiles:
        model.profiles = profiles
        index = payload.get("current_profile_index", 0)
        valid = isinstance(index, int) and 0 <= index < len(profiles)
        model.current_profile_index = index if valid else 0
    model.manual_profile_switching = bool(payload.get("manual_profile_switching", False))
