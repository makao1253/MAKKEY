"""Śledzenie programu na pierwszym planie - do automatycznego doboru profilu.

Hak SetWinEventHook(EVENT_SYSTEM_FOREGROUND) w trybie WINEVENT_OUTOFCONTEXT:
system zgłasza zmianę aktywnego okna przez kolejkę komunikatów wątku GUI
(pompuje ją Qt), więc profil zmienia się od razu, bez odpytywania co chwilę.
"""
from __future__ import annotations

import ctypes
import ntpath
import os
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal

# --- stałe WinAPI ---------------------------------------------------------
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000   # wystarcza też dla procesów admina

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND,
    wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD,
)

user32.SetWinEventHook.argtypes = (
    wintypes.DWORD, wintypes.DWORD, wintypes.HMODULE, WINEVENTPROC,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
)
user32.SetWinEventHook.restype = wintypes.HANDLE
user32.UnhookWinEvent.argtypes = (wintypes.HANDLE,)
user32.UnhookWinEvent.restype = wintypes.BOOL
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL


def foreground_pid() -> int:
    """PID procesu, do którego należy okno na pierwszym planie (0 = brak)."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def process_exe(pid: int) -> str:
    """Nazwa pliku .exe procesu, np. 'chrome.exe' ('' gdy nie da się odczytać)."""
    if not pid:
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return ntpath.basename(buf.value)
    finally:
        kernel32.CloseHandle(handle)


class ForegroundWatcher(QObject):
    """Zgłasza nazwę .exe, gdy na pierwszy plan wychodzi okno innego programu.

    Okna samego MAKKEY są pomijane - kliknięcie w konfigurator nie może
    przestawiać profilu, który właśnie się w nim edytuje.
    """

    appChanged = Signal(str)          # nazwa pliku .exe, np. "chrome.exe"

    def __init__(self, parent=None):
        super().__init__(parent)
        # Wskaźnik na funkcję musi żyć tak długo jak hak - inaczej system
        # zawoła zwolnioną pamięć.
        self._proc = WINEVENTPROC(self._on_event)
        self._hook = None
        self._own_pid = os.getpid()
        self._last_pid = 0

    def start(self) -> bool:
        if not self._hook:
            self._hook = user32.SetWinEventHook(
                EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND,
                None, self._proc, 0, 0, WINEVENT_OUTOFCONTEXT,
            )
        self.check()
        return bool(self._hook)

    def stop(self):
        if self._hook:
            user32.UnhookWinEvent(self._hook)
            self._hook = None

    def check(self):
        """Sprawdza bieżące okno i zgłasza program, jeśli się zmienił."""
        pid = foreground_pid()
        if not pid or pid == self._last_pid:
            return
        # Własny PID też zapamiętujemy: po powrocie z konfiguratora do tego
        # samego programu jego profil ma zostać przywrócony.
        self._last_pid = pid
        if pid == self._own_pid:
            return
        exe = process_exe(pid)
        if exe:
            self.appChanged.emit(exe)

    def _on_event(self, _hook, _event, _hwnd, _obj, _child, _thread, _time):
        self.check()
