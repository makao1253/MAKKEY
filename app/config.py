"""Zapis i odczyt konfiguracji MAKKEY.

Konfiguracja (ustawienia + profile + mapowania + kolory) trzymana jest
w jednym pliku JSON, którego lokalizację użytkownik może zmienić.
Sama ścieżka do tego pliku musi być gdzieś zapamiętana - służy do tego
mały "wskaźnik" w %APPDATA%/MAKKEY/location.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from .constants import (
    DEFAULT_CONFIG_DIR, DEFAULT_CONFIG_PATH, DEFAULT_PANIC_HOTKEY,
    ACTION_NONE, DEFAULT_LED_COLOR, TOTAL_BUTTON_COUNT, PROFILE_BUTTON_INDEX,
    ACTION_PROFILE, DEFAULT_LED_BRIGHTNESS, OLED_SOURCE_CUSTOM,
)
from .theme import DEFAULT_ACCENT

LOCATION_FILE = DEFAULT_CONFIG_DIR / "location.json"
CONFIG_VERSION = 2


@dataclass
class AppConfig:
    """Ustawienia globalne (nie związane z konkretnym profilem)."""
    active: bool = True
    theme: str = "dark"
    accent: str = DEFAULT_ACCENT
    language: str = "pl"
    autostart: bool = False
    minimize_to_tray: bool = True
    check_updates: bool = True          # sprawdzanie repozytorium przy starcie
    panic_hotkey: str = DEFAULT_PANIC_HOTKEY
    panic_hotkey_enabled: bool = True

    # --- wariant sprzętowy ---
    # Opisuje, co fizycznie ma podłączony macropad. Wyłączenie chowa
    # w całym programie sekcje, które bez tego sprzętu i tak nic nie robią.
    has_leds: bool = True
    has_oled: bool = True
    led_brightness: int = DEFAULT_LED_BRIGHTNESS
    oled_source: str = OLED_SOURCE_CUSTOM


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
        "oled_text": profile.oled_text,
        "buttons": {
            str(index): {
                "action_type": mapping.action_type,
                "value": mapping.value,
                "color": mapping.color,
                "enabled": mapping.enabled,
            }
            for index, mapping in sorted(profile.buttons.items())
        },
    }


def _profile_from_dict(data: dict):
    from .models import Profile, ButtonMapping

    profile = Profile(
        name=data.get("name", "Profil"),
        exe=data.get("exe", ""),
        is_default=bool(data.get("is_default", False)),
        enabled=bool(data.get("enabled", True)),
        in_manual_cycle=bool(data.get("in_manual_cycle", False)),
        oled_text=data.get("oled_text", ""),
    )
    stored = data.get("buttons", {})
    for index in range(1, TOTAL_BUTTON_COUNT + 1):
        raw = stored.get(str(index), {})
        default_action = ACTION_PROFILE if index == PROFILE_BUTTON_INDEX else ACTION_NONE
        profile.buttons[index] = ButtonMapping(
            action_type=raw.get("action_type", default_action),
            value=raw.get("value", ""),
            color=raw.get("color", DEFAULT_LED_COLOR),
            # Pliki z wersji 1 nie znały tego pola - tam każdy przycisk działał.
            enabled=bool(raw.get("enabled", True)),
        )
    return profile


def save(cfg: AppConfig, model, path: Path | None = None) -> Path:
    """Zapisuje całość do JSON. Zwraca ścieżkę, pod którą zapisano."""
    target = Path(path) if path else get_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": CONFIG_VERSION,
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
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, "Nie udało się wczytać {path}: {error}", {"path": source, "error": exc}

    settings = dict(payload.get("settings") or {})
    # Wersja 1 trzymała motyw jako flagę logiczną, a tryb testowy klawiatury
    # zniknął razem z przejściem urządzenia na własny deskryptor HID.
    if "dark_theme" in settings and "theme" not in settings:
        settings["theme"] = "dark" if settings["dark_theme"] else "light"
    settings.pop("dark_theme", None)
    settings.pop("accept_any_keyboard", None)

    for key, value in settings.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)

    profiles = [_profile_from_dict(d) for d in payload.get("profiles", [])]
    if profiles:
        model.profiles = profiles
        index = payload.get("current_profile_index", 0)
        model.current_profile_index = index if 0 <= index < len(profiles) else 0
    model.manual_profile_switching = bool(payload.get("manual_profile_switching", False))

    return True, "Wczytano konfigurację z {path}", {"path": source}
