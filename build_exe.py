"""Budowanie pliku MAKKEY.exe (PyInstaller).

Uruchomienie - dowolne z dwóch:
    build_exe.bat          (dwuklik w Eksploratorze)
    python build_exe.py

Efekt: dist/MAKKEY.exe - jeden plik, bez okna konsoli. Brakujące zależności
(PySide6, PyInstaller) skrypt dociąga sam, żeby zbudowanie programu na nowej
maszynie nie wymagało niczego poza Pythonem.

Ikona nie jest trzymana w repozytorium jako gotowy plik: rysuje ją ta sama
funkcja, co ikonę okna (app.theme.make_icon), więc exe i aplikacja nie mogą
się rozjechać. Skrypt składa z niej wielorozdzielczościowy .ico, bo Windows
bierze inny rozmiar na pasek zadań, a inny na kafelek w Eksploratorze.
"""
from __future__ import annotations

import importlib.util
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON_PATH = ROOT / "assets" / "makkey.ico"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def ensure(module: str, package: str) -> bool:
    """Sprawdza pakiet i w razie braku instaluje go przez pip."""
    if importlib.util.find_spec(module) is not None:
        return True
    print(f"[setup] brak pakietu {package} - instaluję przez pip...")
    code = subprocess.call([sys.executable, "-m", "pip", "install", package])
    if code != 0:
        print(f"[BŁĄD] Nie udało się zainstalować {package}.")
        return False
    # find_spec pamięta wynik z poprzedniego sprawdzenia, więc czyścimy pamięć.
    importlib.invalidate_caches()
    return importlib.util.find_spec(module) is not None


def _png_bytes(size: int) -> bytes:
    """Ikona w danym rozmiarze jako PNG (w pamięci)."""
    from PySide6.QtCore import QBuffer, QByteArray, QSize

    from app import theme as T

    pixmap = T.make_icon(size).pixmap(QSize(size, size))
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def build_icon() -> Path:
    """Składa .ico z kilku rozmiarów (wpisy PNG - Windows Vista i nowsze)."""
    from PySide6.QtGui import QGuiApplication

    # QPixmap wymaga istniejącej aplikacji Qt, nawet przy rysowaniu do pamięci.
    app = QGuiApplication.instance() or QGuiApplication([])

    images = [(size, _png_bytes(size)) for size in ICON_SIZES]
    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)

    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, payload = b"", b""
    for size, data in images:
        entries += struct.pack(
            "<BBBBHHII",
            0 if size >= 256 else size,   # 0 oznacza 256 px
            0 if size >= 256 else size,
            0, 0, 1, 32, len(data), offset,
        )
        payload += data
        offset += len(data)

    ICON_PATH.write_bytes(header + entries + payload)
    del app
    return ICON_PATH


def build_exe() -> int:
    icon = build_icon()
    print(f"[ikona] {icon} ({icon.stat().st_size} B)")

    command = [
        sys.executable, "-m", "PyInstaller",
        "--name", "MAKKEY",
        "--onefile",            # jeden plik zamiast katalogu
        "--windowed",           # aplikacja okienkowa - bez konsoli
        "--noconfirm",
        "--clean",
        "--icon", str(icon),
        # Śmieci budowania trzymamy z dala od katalogu projektu.
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        # Moduły, których aplikacja nie używa, a które PyInstaller potrafi
        # dociągnąć "na wszelki wypadek" - bez nich plik jest wyraźnie mniejszy.
        # "email" i "http" muszą zostać: potrzebuje ich urllib, którym
        # app/updater.py rozmawia z GitHubem.
        "--exclude-module", "tkinter",
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",
        "--exclude-module", "xml",
        "--exclude-module", "pdb",
        "--exclude-module", "PySide6.QtNetwork",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtOpenGL",
        "--exclude-module", "PySide6.QtSql",
        "--exclude-module", "PySide6.QtTest",
        "main.py",
    ]
    print("[pyinstaller]", " ".join(command[2:]))
    return subprocess.call(command, cwd=ROOT)


def main() -> int:
    print(f"MAKKEY - budowanie exe  (Python {sys.version.split()[0]})")
    if not ensure("PySide6", "PySide6"):
        return 1
    if not ensure("PyInstaller", "pyinstaller"):
        return 1

    code = build_exe()
    if code != 0:
        print(f"\n[BŁĄD] PyInstaller zakończył się kodem {code}.")
        return code

    exe = DIST_DIR / "MAKKEY.exe"
    if not exe.is_file():
        print("\n[BŁĄD] PyInstaller nie zgłosił błędu, ale pliku exe nie ma.")
        return 1
    print(f"\nGotowe: {exe}  ({exe.stat().st_size / 1_048_576:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
