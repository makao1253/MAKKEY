"""Tłumaczenia interfejsu.

Kluczem jest polski oryginał tekstu (jak w gettext): kod zostaje czytelny,
a brak tłumaczenia kończy się polskim tekstem, a nie pustym polem. Wartości
wstawia się po nazwie: tr("Przycisk {n}", n=3).

Część polskich napisów to zarazem wartości zapisywane w config.json (typy
akcji, akcje multimedialne, źródła tekstu OLED). W pliku zostają po polsku -
tłumaczy się je dopiero przy wyświetlaniu: tr(mapping.action_type). Dzięki
temu konfiguracja działa tak samo w każdym języku.

Język ustawia się przed zbudowaniem okna. Widgety dostają teksty przy
tworzeniu, więc zmiana języka buduje okno od nowa (MainWindow).
"""
from __future__ import annotations

from .lang_en import EN

# (kod, nazwa języka w nim samym) - nazwy celowo nie są tłumaczone
LANGUAGES = [("pl", "Polski"), ("en", "English")]
DEFAULT_LANGUAGE = "pl"

_TABLES: dict[str, dict[str, str]] = {"pl": {}, "en": EN}
_language = DEFAULT_LANGUAGE


def set_language(code: str) -> str:
    """Ustawia język i zwraca faktycznie użyty kod (nieznany = polski)."""
    global _language
    _language = code if code in _TABLES else DEFAULT_LANGUAGE
    return _language


def language() -> str:
    return _language


def tr(text: str, **fields) -> str:
    """Tekst w bieżącym języku, z wstawionymi polami `fields`."""
    result = _TABLES[_language].get(text, text)
    return result.format(**fields) if fields else result
