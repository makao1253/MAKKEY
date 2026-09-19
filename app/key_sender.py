"""Wysyłanie akcji przycisków do systemu (WinAPI SendInput).

Urządzenie nie jest klawiaturą - jego raporty odbiera tylko MAKKEY, więc to
aplikacja musi "nacisnąć" przypisany skrót za użytkownika. SendInput wstawia
zdarzenia do systemowej kolejki wejścia, skąd trafiają do okna na pierwszym
planie - dokładnie tak, jak z prawdziwej klawiatury.

Ograniczenie Windows (UIPI): do programu uruchomionego jako administrator
może pisać tylko program również uruchomiony jako administrator. SendInput
nie zgłasza wtedy żadnego błędu - zdarzenia po prostu giną.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from .constants import (
    MEDIA_PLAY_PAUSE, MEDIA_NEXT_TRACK, MEDIA_PREV_TRACK,
    MEDIA_VOLUME_UP, MEDIA_VOLUME_DOWN, MEDIA_MUTE, MEDIA_LOCK_SCREEN,
)
from .i18n import tr

# --- stałe WinAPI ---------------------------------------------------------
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MAPVK_VK_TO_VSC = 0

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B

user32 = ctypes.WinDLL("user32", use_last_error=True)

ULONG_PTR = wintypes.WPARAM      # liczba o szerokości wskaźnika


# --- struktury ------------------------------------------------------------
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class _INPUT_UNION(ctypes.Union):
    # Mysz i "hardware" nie są używane, ale muszą tu być: od nich zależy
    # rozmiar INPUT, a przy złym cbSize SendInput odrzuca całe wywołanie.
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
user32.MapVirtualKeyW.restype = wintypes.UINT
user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
user32.VkKeyScanW.restype = ctypes.c_short
user32.LockWorkStation.restype = wintypes.BOOL


# --- nazwy klawiszy -------------------------------------------------------
# Nazwy są te same, które zapisuje HotkeyEdit (widgets/common.py).
_MODIFIERS = {"ctrl": VK_CONTROL, "shift": VK_SHIFT, "alt": VK_MENU, "win": VK_LWIN}
_MOD_ORDER = ["ctrl", "shift", "alt", "win"]

_NAMED_KEYS = {
    "esc": 0x1B, "tab": 0x09, "backspace": 0x08, "enter": 0x0D,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pgup": 0x21, "pgdn": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "space": 0x20, "printscreen": 0x2C, "pause": 0x13,
    "capslock": 0x14, "numlock": 0x90, "scrolllock": 0x91, "apps": 0x5D,
    "num+": 0x6B, "num-": 0x6D, "num*": 0x6A, "num/": 0x6F, "num.": 0x6E,
}
_NAMED_KEYS.update({f"f{n}": 0x70 + n - 1 for n in range(1, 25)})
_NAMED_KEYS.update({f"num{n}": 0x60 + n for n in range(10)})

# Interpunkcja leży w różnych układach na różnych klawiszach - kod bierzemy
# z bieżącego układu (VkKeyScanW), a tabela US jest tylko zapasem.
_US_PUNCTUATION = {
    ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF,
    "`": 0xC0, "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}

# Klawisze z bloku rozszerzonego. Bez tej flagi część programów bierze
# strzałki, Home/End itd. za ich odpowiedniki z klawiatury numerycznej.
_EXTENDED = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,   # PgUp..strzałki
    0x2C, 0x2D, 0x2E,                                   # PrtSc, Insert, Delete
    0x5B, 0x5C, 0x5D, 0x6F, 0x90,                       # Win, Apps, Num/, NumLock
    0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3,           # multimedia
}

_MEDIA_KEYS = {
    MEDIA_PLAY_PAUSE: 0xB3, MEDIA_NEXT_TRACK: 0xB0, MEDIA_PREV_TRACK: 0xB1,
    MEDIA_VOLUME_UP: 0xAF, MEDIA_VOLUME_DOWN: 0xAE, MEDIA_MUTE: 0xAD,
}


class KeySendError(Exception):
    """Akcji nie dało się wysłać - treść nadaje się do pokazania w UI."""


# --- zapis skrótu -> kody klawiszy ----------------------------------------
def parse_shortcut(value: str) -> tuple[list[int], int]:
    """'Ctrl+Shift+E' -> ([VK modyfikatorów], VK klawisza głównego).

    Modyfikatory zdejmujemy po kolei z przodu zamiast dzielić całość po '+',
    bo plus bywa częścią nazwy klawisza ('Ctrl+Num+').
    """
    rest = (value or "").strip()
    mods: list[str] = []
    while True:
        head, sep, tail = rest.partition("+")
        name = head.strip().lower()
        if not (sep and tail and name in _MODIFIERS):
            break
        if name not in mods:
            mods.append(name)
        rest = tail

    key = rest.strip()
    if not key:
        raise KeySendError(tr("pusty skrót"))
    vk, required = _key_code(key)
    for name in required:
        if name not in mods:
            mods.append(name)
    mods.sort(key=_MOD_ORDER.index)
    return [_MODIFIERS[name] for name in mods], vk


def _key_code(key: str) -> tuple[int, list[str]]:
    """VK klawisza + modyfikatory, których wymaga do tego bieżący układ."""
    name = key.lower()
    if name in _NAMED_KEYS:
        return _NAMED_KEYS[name], []
    if name in _MODIFIERS:
        return _MODIFIERS[name], []
    if len(key) == 1:
        upper = key.upper()
        if "A" <= upper <= "Z" or "0" <= upper <= "9":
            return ord(upper), []
        scan = user32.VkKeyScanW(key)
        if scan != -1 and (scan & 0xFF) != 0xFF:
            state = (scan >> 8) & 0xFF
            required = [mod for bit, mod in ((1, "shift"), (2, "ctrl"), (4, "alt"))
                        if state & bit]
            return scan & 0xFF, required
        if key in _US_PUNCTUATION:
            return _US_PUNCTUATION[key], []
    raise KeySendError(tr('nieznany klawisz "{key}"', key=key))


# --- wysyłka --------------------------------------------------------------
def _key_event(vk: int, up: bool) -> INPUT:
    flags = KEYEVENTF_KEYUP if up else 0
    if vk in _EXTENDED:
        flags |= KEYEVENTF_EXTENDEDKEY
    event = INPUT(type=INPUT_KEYBOARD)
    # Kod skanowania obok VK - część programów patrzy właśnie na niego.
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC) & 0xFF
    event.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags)
    return event


def _unicode_event(unit: int, up: bool) -> INPUT:
    event = INPUT(type=INPUT_KEYBOARD)
    event.ki = KEYBDINPUT(
        wVk=0, wScan=unit,
        dwFlags=KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0),
    )
    return event


def _send(events: list[INPUT]) -> None:
    """Całość idzie jednym wywołaniem - fizyczne klawisze nie wpadną w środek."""
    if not events:
        return
    array = (INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), array, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise KeySendError(tr(
            "system przyjął {sent} z {total} zdarzeń (błąd {code})",
            sent=sent, total=len(events), code=ctypes.get_last_error(),
        ))


def send_shortcut(value: str) -> None:
    """Naciska i puszcza skrót: modyfikatory, klawisz, potem puszczenie
    wszystkiego w odwrotnej kolejności."""
    mods, key = parse_shortcut(value)
    keys = [*mods, key]
    _send([_key_event(vk, up=False) for vk in keys]
          + [_key_event(vk, up=True) for vk in reversed(keys)])


def type_text(text: str) -> None:
    """Wpisuje tekst jako znaki Unicode - niezależnie od układu klawiatury,
    więc polskie litery też przechodzą."""
    data = (text or "").encode("utf-16-le")
    events: list[INPUT] = []
    for i in range(0, len(data), 2):
        unit = int.from_bytes(data[i:i + 2], "little")
        events += [_unicode_event(unit, up=False), _unicode_event(unit, up=True)]
    _send(events)


def send_media(name: str) -> None:
    """Klawisz multimedialny albo blokada ekranu."""
    if name == MEDIA_LOCK_SCREEN:
        if not user32.LockWorkStation():
            raise KeySendError(tr("blokada ekranu nie powiodła się (błąd {code})",
                                  code=ctypes.get_last_error()))
        return
    vk = _MEDIA_KEYS.get(name)
    if vk is None:
        raise KeySendError(tr('nieznana akcja "{name}"', name=name))
    _send([_key_event(vk, up=False), _key_event(vk, up=True)])
