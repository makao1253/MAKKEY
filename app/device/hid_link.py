"""Łącze z urządzeniem MAKKEY (surowy HID, vendor-defined usage page 0xFF00).

Urządzenie NIE jest klawiaturą - ma własny deskryptor raportu, więc:

* **odczyt** idzie przez Windows Raw Input zarejestrowany na usage page
  `0xFF00` / usage `0x01`. Raw Input dostarcza komplet bajtów raportu razem
  z uchwytem urządzenia źródłowego, nie wymaga otwierania urządzenia na
  odczyt i działa także wtedy, gdy okno nie ma fokusu;
* **zapis** (kolory diod, tekst na OLED) idzie przez zwykły `WriteFile` na
  uchwycie z `CreateFileW` - urządzenie nie jest klawiaturą, więc system
  nie trzyma go na wyłączność.

Urządzenie rozpoznajemy po nazwie produktu z deskryptora USB ("MAKKEY").
VID/PID są tylko zapasem na wypadek, gdyby nazwy nie dało się odczytać -
dzięki temu podmiana PID-u w firmware niczego nie psuje. Wszystko, co nie
zgadza się jednocześnie z usage page i nazwą, jest pomijane.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QAbstractNativeEventFilter, Signal

from ..constants import (
    DEVICE_PRODUCT_STRING, DEFAULT_VENDOR_ID, DEFAULT_PRODUCT_ID,
    HID_USAGE_PAGE_VENDOR, HID_USAGE_MAKKEY, REPORT_ID_IN, REPORT_ID_OUT,
    OUT_REPORT_SIZE, TOTAL_BUTTON_COUNT, OLED_MAX_CHARS,
    EVENT_BUTTONS, EVENT_PONG, EVENT_ACK,
    CMD_SET_LED_ONE, CMD_SET_LED_ALL, CMD_SET_BRIGHTNESS, CMD_SAVE_TO_FLASH,
    CMD_OLED_TEXT, CMD_OLED_CLEAR, CMD_PING,
)
from ..i18n import tr

# --- stałe WinAPI ---------------------------------------------------------
WM_INPUT = 0x00FF
WM_INPUT_DEVICE_CHANGE = 0x00FE

RID_INPUT = 0x10000003
RIDI_DEVICENAME = 0x20000007
RIDI_DEVICEINFO = 0x2000000B
RIM_TYPEHID = 2

RIDEV_INPUTSINK = 0x00000100     # zdarzenia także gdy okno nie ma fokusu
RIDEV_DEVNOTIFY = 0x00002000     # powiadomienia o pod/odłączeniu
RIDEV_REMOVE = 0x00000001

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

HIDP_STATUS_SUCCESS = 0x00110000

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
hid = ctypes.WinDLL("hid", use_last_error=True)


# --- struktury ------------------------------------------------------------
class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [("hDevice", wintypes.HANDLE), ("dwType", wintypes.DWORD)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWHID(ctypes.Structure):
    """Nagłówek porcji raportów HID; bajty raportu leżą zaraz za nim."""
    _fields_ = [
        ("dwSizeHid", wintypes.DWORD),   # długość jednego raportu
        ("dwCount", wintypes.DWORD),     # ile raportów w tej porcji
        ("bRawData", ctypes.c_ubyte * 1),
    ]


class RAWINPUTHID(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("hid", RAWHID)]


class RID_DEVICE_INFO_MOUSE(ctypes.Structure):
    _fields_ = [("dwId", wintypes.DWORD), ("dwNumberOfButtons", wintypes.DWORD),
                ("dwSampleRate", wintypes.DWORD), ("fHasHorizontalWheel", wintypes.BOOL)]


class RID_DEVICE_INFO_KEYBOARD(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSubType", wintypes.DWORD),
                ("dwKeyboardMode", wintypes.DWORD),
                ("dwNumberOfFunctionKeys", wintypes.DWORD),
                ("dwNumberOfIndicators", wintypes.DWORD),
                ("dwNumberOfKeysTotal", wintypes.DWORD)]


class RID_DEVICE_INFO_HID(ctypes.Structure):
    _fields_ = [("dwVendorId", wintypes.DWORD), ("dwProductId", wintypes.DWORD),
                ("dwVersionNumber", wintypes.DWORD),
                ("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT)]


class _RID_INFO_UNION(ctypes.Union):
    _fields_ = [("mouse", RID_DEVICE_INFO_MOUSE),
                ("keyboard", RID_DEVICE_INFO_KEYBOARD),
                ("hid", RID_DEVICE_INFO_HID)]


class RID_DEVICE_INFO(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("cbSize", wintypes.DWORD), ("dwType", wintypes.DWORD),
                ("u", _RID_INFO_UNION)]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT), ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
    ]


# offset bajtów raportu wewnątrz bufora RAWINPUT
_RAW_DATA_OFFSET = RAWINPUTHID.hid.offset + RAWHID.bRawData.offset


# --- wyszukiwanie urządzenia ----------------------------------------------
class DeviceInfo:
    """Jedno urządzenie HID widziane przez Raw Input."""

    def __init__(self, handle: int, path: str, product: str,
                 vid: int, pid: int, usage_page: int, usage: int):
        self.handle = handle
        self.path = path
        self.product = product
        self.vid = vid
        self.pid = pid
        self.usage_page = usage_page
        self.usage = usage

    @property
    def vid_pid(self) -> str:
        return f"{self.vid:04X}:{self.pid:04X}"

    @property
    def usage_text(self) -> str:
        return f"0x{self.usage_page:04X} / 0x{self.usage:02X}"

    def is_makkey(self) -> bool:
        """Czy to NASZE urządzenie - reszta świata ma być pomijana."""
        if self.usage_page != HID_USAGE_PAGE_VENDOR or self.usage != HID_USAGE_MAKKEY:
            return False
        if self.product:
            return DEVICE_PRODUCT_STRING.lower() in self.product.lower()
        # Nazwy nie zawsze da się odczytać (np. gdy sterownik jej nie wystawia).
        return self.vid == DEFAULT_VENDOR_ID and self.pid == DEFAULT_PRODUCT_ID


def _device_path(handle) -> str:
    """Ścieżka urządzenia, np. \\\\?\\HID#VID_0483&PID_572B#..."""
    size = wintypes.UINT(0)
    user32.GetRawInputDeviceInfoW(handle, RIDI_DEVICENAME, None, ctypes.byref(size))
    if size.value == 0:
        return ""
    buf = ctypes.create_unicode_buffer(size.value)
    if user32.GetRawInputDeviceInfoW(
        handle, RIDI_DEVICENAME, buf, ctypes.byref(size)
    ) == wintypes.UINT(-1).value:
        return ""
    return buf.value


def _device_hid_info(handle) -> RID_DEVICE_INFO_HID | None:
    info = RID_DEVICE_INFO()
    info.cbSize = ctypes.sizeof(RID_DEVICE_INFO)
    size = wintypes.UINT(ctypes.sizeof(RID_DEVICE_INFO))
    got = user32.GetRawInputDeviceInfoW(
        handle, RIDI_DEVICEINFO, ctypes.byref(info), ctypes.byref(size)
    )
    if got == wintypes.UINT(-1).value or info.dwType != RIM_TYPEHID:
        return None
    return info.hid


def _product_string(device_path: str) -> str:
    """Nazwa produktu z deskryptora USB.

    Otwieramy urządzenie z dwDesiredAccess = 0 - to wystarcza do zapytań
    i nie koliduje z niczym, kto już z niego korzysta.
    """
    if not device_path:
        return ""
    handle = kernel32.CreateFileW(
        device_path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, 0, None,
    )
    if handle == INVALID_HANDLE_VALUE or handle is None:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(256)
        if hid.HidD_GetProductString(handle, buf, ctypes.sizeof(buf)):
            return buf.value.strip()
        return ""
    finally:
        kernel32.CloseHandle(handle)


def enumerate_hid_devices() -> list[DeviceInfo]:
    """Wszystkie urządzenia HID (bez myszy i klawiatur) widziane przez system."""
    count = wintypes.UINT(0)
    size = ctypes.sizeof(RAWINPUTDEVICELIST)
    user32.GetRawInputDeviceList(None, ctypes.byref(count), size)
    if count.value == 0:
        return []

    array = (RAWINPUTDEVICELIST * count.value)()
    got = user32.GetRawInputDeviceList(array, ctypes.byref(count), size)
    if got == wintypes.UINT(-1).value:
        return []

    result: list[DeviceInfo] = []
    for i in range(got):
        entry = array[i]
        if entry.dwType != RIM_TYPEHID:
            continue
        info = _device_hid_info(entry.hDevice)
        if info is None:
            continue
        path = _device_path(entry.hDevice)
        result.append(DeviceInfo(
            handle=entry.hDevice, path=path, product=_product_string(path),
            vid=info.dwVendorId, pid=info.dwProductId,
            usage_page=info.usUsagePage, usage=info.usUsage,
        ))
    return result


# --- transliteracja tekstu na OLED ----------------------------------------
# Standardowy font SSD1306 nie ma polskich znaków, a firmware i tak filtruje
# je u siebie - robimy to samo po stronie hosta, żeby w podglądzie na żywo
# widzieć dokładnie to, co pojawi się na wyświetlaczu.
_ASCII_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
    "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N",
    "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
})


def to_oled_ascii(text: str) -> str:
    """Tekst przycięty do jednej linii wyświetlacza, bez ogonków."""
    clean = (text or "").translate(_ASCII_MAP)
    clean = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in clean)
    return clean[:OLED_MAX_CHARS]


# --- łącze ----------------------------------------------------------------
class MakkeyLink(QObject, QAbstractNativeEventFilter):
    """Odbiór raportów IN i wysyłka raportów OUT do macropada MAKKEY."""

    buttonPressed = Signal(int)
    buttonReleased = Signal(int)
    deviceStateChanged = Signal(bool, str)   # (podłączone, opis)
    rawEvent = Signal(str)                   # linia do strumienia zdarzeń
    firmwareInfo = Signal(str)               # wersja z odpowiedzi na PING

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)

        self.device: DeviceInfo | None = None

        self._enabled = True
        self._handles: set[int] = set()
        self._held: set[int] = set()
        self._write_handle = None
        self._out_size = OUT_REPORT_SIZE
        self._registered = False
        self._hwnd = 0

    # ------------------------------------------------------------------ API
    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Wstrzymanie odbioru. Klawisze trzymane w chwili wyłączenia trzeba
        zgłosić jako puszczone - inaczej zostałyby zapalone na podglądzie na
        zawsze, bo ich puszczenia już nie zobaczymy."""
        value = bool(value)
        if value == self._enabled:
            return
        self._enabled = value
        if not value:
            self.release_held()

    def release_held(self):
        for index in sorted(self._held):
            self.buttonReleased.emit(index)
        self._held.clear()

    def start(self, hwnd: int) -> bool:
        """Rejestruje okno jako odbiorcę raportów z urządzeń 0xFF00."""
        self._hwnd = hwnd
        device = RAWINPUTDEVICE(
            usUsagePage=HID_USAGE_PAGE_VENDOR,
            usUsage=HID_USAGE_MAKKEY,
            dwFlags=RIDEV_INPUTSINK | RIDEV_DEVNOTIFY,
            hwndTarget=wintypes.HWND(hwnd),
        )
        ok = user32.RegisterRawInputDevices(
            ctypes.byref(device), 1, ctypes.sizeof(RAWINPUTDEVICE)
        )
        self._registered = bool(ok)
        if ok:
            self.rescan()
        return self._registered

    def rescan(self) -> bool:
        """Szuka MAKKEY wśród podłączonych urządzeń HID."""
        self._close_write_handle()
        self._handles.clear()
        self.device = None

        for info in enumerate_hid_devices():
            if not info.is_makkey():
                continue
            self._handles.add(info.handle)
            if self.device is None:
                self.device = info

        if self.device is not None:
            self._open_write_handle(self.device.path)

        connected = bool(self._handles)
        label = self.device.product if self.device and self.device.product else DEVICE_PRODUCT_STRING
        self.deviceStateChanged.emit(connected, label)
        return connected

    def stop(self):
        """Wyrejestrowuje odbiór i zamyka uchwyt zapisu."""
        if self._registered:
            device = RAWINPUTDEVICE(
                usUsagePage=HID_USAGE_PAGE_VENDOR,
                usUsage=HID_USAGE_MAKKEY,
                dwFlags=RIDEV_REMOVE,
                hwndTarget=wintypes.HWND(0),
            )
            user32.RegisterRawInputDevices(
                ctypes.byref(device), 1, ctypes.sizeof(RAWINPUTDEVICE)
            )
            self._registered = False
        self._close_write_handle()

    @property
    def is_connected(self) -> bool:
        return bool(self._handles)

    @property
    def vid_pid(self) -> str:
        return self.device.vid_pid if self.device else ""

    @property
    def usage_text(self) -> str:
        return self.device.usage_text if self.device else ""

    # ------------------------------------------------------- raporty wyjściowe
    def send(self, command: int, payload: bytes = b"") -> bool:
        """Wysyła raport OUT: [ID][kod komendy][parametry...][zera].

        Wstrzymany MAKKEY nie steruje urządzeniem - blokada stoi tutaj, żeby
        żadna ścieżka wysyłki nie potrafiła jej obejść.
        """
        if self._write_handle is None or not self._enabled:
            return False
        body = bytes([REPORT_ID_OUT, command]) + payload
        if len(body) > self._out_size:
            return False
        buf = ctypes.create_string_buffer(body.ljust(self._out_size, b"\x00"),
                                          self._out_size)
        written = wintypes.DWORD(0)
        ok = kernel32.WriteFile(
            self._write_handle, buf, self._out_size, ctypes.byref(written), None
        )
        if not ok:
            # Niektóre stosy HID nie przyjmują zapisu na potoku przerwaniowym -
            # wtedy zostaje SET_REPORT po potoku kontrolnym.
            ok = hid.HidD_SetOutputReport(self._write_handle, buf, self._out_size)
        return bool(ok)

    def set_led(self, index: int, color: str) -> bool:
        r, g, b = _rgb(color)
        return self.send(CMD_SET_LED_ONE, bytes([index, r, g, b]))

    def set_all_leds(self, colors: dict[int, str]) -> bool:
        payload = bytearray()
        for i in range(1, TOTAL_BUTTON_COUNT + 1):
            payload += bytes(_rgb(colors.get(i, "#000000")))
        return self.send(CMD_SET_LED_ALL, bytes(payload))

    def set_brightness(self, value: int) -> bool:
        return self.send(CMD_SET_BRIGHTNESS, bytes([max(0, min(255, int(value)))]))

    def save_to_flash(self) -> bool:
        return self.send(CMD_SAVE_TO_FLASH)

    def oled_text(self, line: int, text: str) -> bool:
        ascii_text = to_oled_ascii(text).encode("ascii", "replace")
        return self.send(CMD_OLED_TEXT,
                         bytes([line & 0x01, len(ascii_text)]) + ascii_text)

    def oled_clear(self) -> bool:
        return self.send(CMD_OLED_CLEAR)

    def ping(self) -> bool:
        return self.send(CMD_PING)

    # ------------------------------------------------- filtr zdarzeń natywnych
    def nativeEventFilter(self, event_type, message):
        if event_type != b"windows_generic_MSG":
            return False, 0
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
        except (TypeError, ValueError):
            return False, 0

        if msg.message == WM_INPUT_DEVICE_CHANGE:
            self.rescan()
        elif msg.message == WM_INPUT and self.enabled:
            self._handle_input(msg.lParam)

        # Raportów nie konsumujemy - i tak nikt inny ich nie dostaje.
        return False, 0

    def _handle_input(self, lparam: int):
        size = wintypes.UINT(0)
        header_size = ctypes.sizeof(RAWINPUTHEADER)
        user32.GetRawInputData(
            wintypes.HANDLE(lparam), RID_INPUT, None,
            ctypes.byref(size), header_size,
        )
        if size.value < ctypes.sizeof(RAWINPUTHID):
            return

        buf = ctypes.create_string_buffer(size.value)
        read = user32.GetRawInputData(
            wintypes.HANDLE(lparam), RID_INPUT, buf,
            ctypes.byref(size), header_size,
        )
        if read in (0, wintypes.UINT(-1).value):
            return

        raw = ctypes.cast(buf, ctypes.POINTER(RAWINPUTHID)).contents
        if raw.header.dwType != RIM_TYPEHID:
            return
        if raw.header.hDevice not in self._handles:
            return

        one = raw.hid.dwSizeHid
        count = raw.hid.dwCount
        if one == 0 or count == 0:
            return
        data = ctypes.string_at(ctypes.addressof(buf) + _RAW_DATA_OFFSET, one * count)
        # Jedna porcja WM_INPUT potrafi nieść kilka raportów naraz.
        for i in range(count):
            self._handle_report(data[i * one:(i + 1) * one])

    def _handle_report(self, report: bytes):
        if len(report) < 4 or report[0] != REPORT_ID_IN:
            return
        payload = report[1:]
        kind = payload[0]

        if kind == EVENT_BUTTONS:
            self._handle_buttons(payload)
        elif kind == EVENT_PONG:
            version = f"{payload[1]}.{payload[2]}.{payload[3]}"
            self.rawEvent.emit(tr("pong - firmware {version}", version=version))
            self.firmwareInfo.emit(version)
        elif kind == EVENT_ACK:
            status = "OK" if payload[2] == 0 else tr("błąd {code}", code=payload[2])
            self.rawEvent.emit(tr("ack komendy 0x{cmd:02X} - {status}",
                                  cmd=payload[1], status=status))

    def _handle_buttons(self, payload: bytes):
        bitmap = payload[1] | (payload[2] << 8)
        state = {i + 1 for i in range(TOTAL_BUTTON_COUNT) if bitmap & (1 << i)}

        for index in sorted(state - self._held):
            self.rawEvent.emit(tr("przycisk {n} - wciśnięty", n=index))
            self.buttonPressed.emit(index)
        for index in sorted(self._held - state):
            self.buttonReleased.emit(index)
        self._held = state

    # --------------------------------------------------------- uchwyt zapisu
    def _open_write_handle(self, path: str):
        if not path:
            return
        handle = kernel32.CreateFileW(
            path, GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None,
        )
        if handle == INVALID_HANDLE_VALUE or handle is None:
            self._write_handle = None
            return
        self._write_handle = wintypes.HANDLE(handle)
        self._out_size = _output_report_length(self._write_handle) or OUT_REPORT_SIZE

    def _close_write_handle(self):
        if self._write_handle is not None:
            kernel32.CloseHandle(self._write_handle)
            self._write_handle = None


def _output_report_length(handle) -> int:
    """Rozmiar raportu OUT deklarowany przez urządzenie (0 = nie udało się)."""
    preparsed = ctypes.c_void_p()
    if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
        return 0
    try:
        caps = HIDP_CAPS()
        if hid.HidP_GetCaps(preparsed, ctypes.byref(caps)) != HIDP_STATUS_SUCCESS:
            return 0
        return int(caps.OutputReportByteLength)
    finally:
        hid.HidD_FreePreparsedData(preparsed)


def _rgb(color: str) -> tuple[int, int, int]:
    """#RRGGBB -> (R, G, B). Kolejność GRB ustawia już firmware."""
    value = (color or "").lstrip("#")
    if len(value) != 6:
        return (0, 0, 0)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return (0, 0, 0)
