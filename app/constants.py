"""Stałe konfiguracyjne aplikacji MAKKEY."""
from pathlib import Path
import os

APP_NAME = "MAKKEY"
APP_VERSION = "1.1.2"
APP_WINDOW_TITLE = f"{APP_NAME} {APP_VERSION}"

# --- geometria urządzenia -------------------------------------------------
# 12 przycisków w matrycy 4 kolumny x 3 wiersze; przycisk 13 znajduje się
# NAD przyciskiem 1 (lewy górny róg), a po jego prawej stronie - wyświetlacz
# OLED 0.91".
GRID_COLUMNS = 4
GRID_ROWS = 3
GRID_BUTTON_COUNT = GRID_COLUMNS * GRID_ROWS  # 12
PROFILE_BUTTON_INDEX = 13
TOTAL_BUTTON_COUNT = GRID_BUTTON_COUNT + 1  # 13

# --- profile ---------------------------------------------------------------
# Przy ręcznym przełączaniu (przyciskiem 13) cykl obejmuje maksymalnie
# 4 profile - żeby dało się je obejść kilkoma naciśnięciami i żeby zmieściły
# się na wyświetlaczu OLED.
MAX_MANUAL_PROFILES = 4

# --- OLED 0.91" (SSD1306, 128x32 px, I2C) ---------------------------------
# Firmware rysuje nazwę aktywnego profilu fontem 11x18: jedna linia,
# 128 / 11 = 11 znaków - dłuższa nazwa jest ucinana.
OLED_WIDTH_PX = 128
OLED_HEIGHT_PX = 32
OLED_MAX_CHARS = 11
OLED_MAX_LINES = 1

# --- USB / HID -------------------------------------------------------------
# Urządzenie zgłasza się własnym, surowym deskryptorem (vendor-defined usage
# page 0xFF00) i NIE jest klawiaturą. Wyszukujemy je po nazwie produktu
# z deskryptora USB, a VID/PID służą już tylko do potwierdzenia tożsamości -
# dzięki temu zmiana PID-u w firmware niczego nie psuje.
DEVICE_MANUFACTURER_STRING = "MAK"
DEVICE_PRODUCT_STRING = "MAKKEY"     # iProduct - po tym szuka aplikacja
DEFAULT_VENDOR_ID = 0x0483
DEFAULT_PRODUCT_ID = 0x572B

HID_USAGE_PAGE_VENDOR = 0xFF00       # Usage Page (Vendor Defined)
HID_USAGE_MAKKEY = 0x01              # Usage (0x01) - kolekcja aplikacyjna

REPORT_ID_IN = 0x01                  # urządzenie -> host
REPORT_ID_OUT = 0x02                 # host -> urządzenie
IN_REPORT_SIZE = 9                   # 1 bajt ID + 8 bajtów payloadu
OUT_REPORT_SIZE = 64                 # 1 bajt ID + 63 bajty payloadu

# typy zdarzeń w bajcie 0 payloadu raportu IN
EVENT_BUTTONS = 0x01                 # stan przycisków
EVENT_PONG = 0x02                    # odpowiedź na PING (wersja firmware)
EVENT_ACK = 0x03                     # potwierdzenie komendy

# flagi firmware (bajt 4 payloadu raportu IN)
FW_FLAG_DEBUG_UART = 0x01
FW_FLAG_OLED_PRESENT = 0x02

# kody komend w raporcie OUT (bajt 0 payloadu)
CMD_SET_LED_ONE = 0x10
CMD_SET_LED_ALL = 0x11
CMD_SAVE_TO_FLASH = 0x12
CMD_SET_BRIGHTNESS = 0x13
CMD_OLED_TEXT = 0x20
CMD_OLED_CLEAR = 0x21
CMD_PING = 0x30

# 13 diod x pełna biel to ~780 mA przy 500 mA z USB - firmware ogranicza
# jasność sprzętowo, a my startujemy z tej samej wartości co ono.
DEFAULT_LED_BRIGHTNESS = 64

# --- aktualizacje ----------------------------------------------------------
# Wersja uruchomiona z kodu aktualizuje się przez git (pull z tej gałęzi),
# plik exe - z najnowszego wydania (Releases) z dołączonym MAKKEY.exe.
UPDATE_REPO = "makao1253/MAKKEY"
UPDATE_BRANCH = "main"
UPDATE_EXE_ASSET = "MAKKEY.exe"
UPDATE_REPO_URL = f"https://github.com/{UPDATE_REPO}"

# --- pliki / ścieżki -------------------------------------------------------
DEFAULT_CONFIG_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "MAKKEY"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

# --- skrót awaryjny --------------------------------------------------------
DEFAULT_PANIC_HOTKEY = "Ctrl+Alt+Shift+Esc"

# --- typy akcji ------------------------------------------------------------
ACTION_NONE = "Brak akcji"
ACTION_SHORTCUT = "Skrót klawiszowy"
ACTION_TEXT = "Wpisz tekst"
ACTION_MEDIA = "Media / system"
ACTION_PROFILE = "Zmiana profilu"

# Akcja "Zmiana profilu" jest dostępna WYŁĄCZNIE dla przycisku 13.
ACTION_TYPES_STANDARD = [ACTION_NONE, ACTION_SHORTCUT, ACTION_TEXT, ACTION_MEDIA]
ACTION_TYPES_PROFILE_BUTTON = [ACTION_PROFILE]

# wartości akcji "Media / system" - zapisywane w config.json tym tekstem
MEDIA_PLAY_PAUSE = "Odtwórz / pauza"
MEDIA_NEXT_TRACK = "Następny utwór"
MEDIA_PREV_TRACK = "Poprzedni utwór"
MEDIA_VOLUME_UP = "Głośniej"
MEDIA_VOLUME_DOWN = "Ciszej"
MEDIA_MUTE = "Wycisz"
MEDIA_LOCK_SCREEN = "Blokada ekranu"
MEDIA_ACTIONS = [
    MEDIA_PLAY_PAUSE, MEDIA_NEXT_TRACK, MEDIA_PREV_TRACK,
    MEDIA_VOLUME_UP, MEDIA_VOLUME_DOWN, MEDIA_MUTE, MEDIA_LOCK_SCREEN,
]

# --- domyślna paleta kolorów LED (WS2812B) --------------------------------
LED_PRESET_COLORS = [
    "#2F80ED", "#27AE60", "#EB5757", "#F2C94C",
    "#9B51E0", "#00BCD4", "#FF7A00", "#FFFFFF",
]
DEFAULT_LED_COLOR = "#2F80ED"
