"""Motyw aplikacji (ciemny / jasny) + zasoby generowane programowo.

Kolory są zwykłymi zmiennymi modułu, a `apply_mode()` je przepina. Widgety
czytają je dopiero w trakcie rysowania, więc zmiana motywu działa od razu -
wystarczy podać aplikacji nowy arkusz stylów.

Paleta i arkusz stylów są wspólne z MAKMOUSE: obie aplikacje tego samego
autora mają wyglądać jak jeden program, a przy ewentualnym scaleniu nie
trzeba będzie niczego uzgadniać.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
)

MODES = ("dark", "light")

# Kolory znaczeniowe są wspólne dla obu motywów - stan urządzenia ma wyglądać
# tak samo niezależnie od tego, czy tło jest jasne czy ciemne.
OK = "#1DB870"
WARN = "#E0A500"
BAD = "#E23B3B"

DEFAULT_ACCENT = "#0080FF"

# Dziesięć podstawowych kolorów wiodących (Ustawienia -> Kolor wiodący).
# Celowo bez pełnej palety RGB: krótka lista trzyma interfejs spójnym.
ACCENTS: list[tuple[str, str]] = [
    ("Niebieski", "#0080FF"),
    ("Granatowy", "#4F5BD5"),
    ("Fioletowy", "#8B5CF6"),
    ("Różowy", "#EC4899"),
    ("Czerwony", "#E23B3B"),
    ("Pomarańczowy", "#F97316"),
    ("Żółty", "#E0A500"),
    ("Zielony", "#1DB870"),
    ("Turkusowy", "#14B8A6"),
    ("Grafitowy", "#6B7A90"),
]

# Odcienie wiodące (jaśniejszy / ciemniejszy) wyliczamy z wybranego koloru,
# więc każdy z dziesięciu wyborów dostaje komplet stanów hover/pressed.
ACCENT = DEFAULT_ACCENT
ACCENT_DIM = "#0059B3"
ACCENT_SOFT = "#3D9DFF"


def accent_name(value: str) -> str:
    """Nazwa koloru z listy (nieznany kod = po prostu sam kod)."""
    for name, code in ACCENTS:
        if code.lower() == (value or "").lower():
            return name
    return value


def apply_accent(value: str) -> str:
    """Ustawia kolor wiodący i zwraca faktycznie użyty kod."""
    global ACCENT, ACCENT_DIM, ACCENT_SOFT
    col = QColor(value)
    if not col.isValid():
        col = QColor(DEFAULT_ACCENT)
    ACCENT = col.name().upper()
    ACCENT_DIM = col.darker(145).name().upper()
    ACCENT_SOFT = col.lighter(128).name().upper()
    return ACCENT


_PALETTES = {
    "dark": {
        "BG": "#101216", "PANEL": "#191C22", "PANEL_HI": "#20242C",
        "BORDER": "#2A2F39", "TEXT": "#E6E9EF", "TEXT_DIM": "#8A93A3",
        "FIELD": "#14171D", "HOVER": "#262B34", "HOVER_BORDER": "#3A4150",
        "PRESSED": "#2E343F", "DIS_TEXT": "#5A6170", "DIS_BG": "#171A20",
        "TRACK": "#2A2F39", "SCROLL": "#333945", "SCROLL_HI": "#414957",
        "TOOLTIP": "#23272F", "SEL_TEXT": "#EAF4FF", "TOGGLE_OFF": "#333945",
        "CAPTURE_BG": "#101F30",
        "DANGER_BORDER": "#5A2A2A", "DANGER_TEXT": "#FF9E9E", "DANGER_BG": "#2A1C1C",
    },
    "light": {
        "BG": "#EEF1F6", "PANEL": "#FFFFFF", "PANEL_HI": "#F4F6FA",
        "BORDER": "#D5DBE5", "TEXT": "#171A20", "TEXT_DIM": "#5D6675",
        "FIELD": "#FFFFFF", "HOVER": "#E8EDF5", "HOVER_BORDER": "#B9C2D0",
        "PRESSED": "#DCE3EE", "DIS_TEXT": "#A0A8B5", "DIS_BG": "#F0F2F6",
        "TRACK": "#D5DBE5", "SCROLL": "#C4CCD9", "SCROLL_HI": "#AEB7C6",
        "TOOLTIP": "#FFFFFF", "SEL_TEXT": "#FFFFFF", "TOGGLE_OFF": "#C4CCD9",
        "CAPTURE_BG": "#E6F1FF",
        "DANGER_BORDER": "#E3B4B4", "DANGER_TEXT": "#B02525", "DANGER_BG": "#FBECEC",
    },
}

_mode = "dark"

# Nazwy widoczne dla reszty aplikacji (T.BG, T.TEXT, ...). Ustawiane w apply_mode.
BG = PANEL = PANEL_HI = BORDER = TEXT = TEXT_DIM = FIELD = ""
HOVER = HOVER_BORDER = PRESSED = DIS_TEXT = DIS_BG = TRACK = ""
SCROLL = SCROLL_HI = TOOLTIP = SEL_TEXT = TOGGLE_OFF = CAPTURE_BG = ""
DANGER_BORDER = DANGER_TEXT = DANGER_BG = ""


def apply_mode(name: str) -> str:
    """Przełącza motyw i zwraca jego nazwę (nieznana nazwa = ciemny)."""
    global _mode
    _mode = name if name in _PALETTES else "dark"
    globals().update(_PALETTES[_mode])
    return _mode


def mode() -> str:
    return _mode


apply_mode("dark")


def _qss(arrow: str) -> str:
    image = f'image: url("{arrow}"); ' if arrow else ""
    return f"""
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QWidget#Root, QMainWindow, QDialog {{ background: {BG}; }}

QFrame#Card {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QFrame#CardFlat {{
    background: {PANEL_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#CardAccent {{
    background: {PANEL};
    border: 1px solid {ACCENT};
    border-radius: 10px;
}}
QLabel#CardTitle {{
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_DIM};
    letter-spacing: 1px;
}}
QLabel#Hint {{ color: {TEXT_DIM}; font-size: 12px; }}
QLabel#Big {{ font-size: 16px; font-weight: 600; }}
QLabel#Brand {{ font-size: 20px; font-weight: 700; letter-spacing: 3px; color: {TEXT}; }}
QLabel#BrandSub {{ font-size: 11px; color: {TEXT_DIM}; letter-spacing: 1px; }}
QLabel#Mono, QPlainTextEdit#Mono, QTextEdit#Mono, QLineEdit#Mono {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
}}

/* Nagłówek zaznaczonego przycisku w zakładce "Przyciski". */
QFrame#KeyHeader {{
    background: {CAPTURE_BG};
    border: 1px solid {ACCENT};
    border-radius: 8px;
}}
QLabel#KeyNumber {{ font-size: 24px; font-weight: 800; color: {ACCENT}; }}

/* Odznaka licznika profili w cyklu ręcznym. */
QLabel#Badge {{
    background: {CAPTURE_BG};
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 9px;
    padding: 1px 9px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#BadgeFull {{
    background: transparent;
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 1px 9px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton {{
    background: {PANEL_HI};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 5px 12px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {HOVER}; border-color: {HOVER_BORDER}; }}
QPushButton:pressed {{ background: {PRESSED}; }}
QPushButton:disabled {{ color: {DIS_TEXT}; background: {DIS_BG}; }}
QPushButton#Primary {{
    background: {ACCENT}; border: none; color: #FFFFFF; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {ACCENT_SOFT}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_DIM}; }}
QPushButton#Danger {{ border-color: {DANGER_BORDER}; color: {DANGER_TEXT}; }}
QPushButton#Danger:hover {{ background: {DANGER_BG}; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {BORDER}; }}
QPushButton#Info {{
    background: transparent; border: 1px solid {ACCENT}; border-radius: 15px;
    color: {ACCENT}; font-family: Georgia, "Times New Roman", serif;
    font-size: 16px; font-weight: 700; font-style: italic; padding: 0;
}}
QPushButton#Info:hover {{ background: {ACCENT}; color: #FFFFFF; }}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 4px 8px;
    selection-background-color: {ACCENT_DIM};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled, QPlainTextEdit:disabled {{ color: {DIS_TEXT}; background: {DIS_BG}; }}
QLineEdit#Capture {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    color: {ACCENT};
}}
QLineEdit#Capture[recording="true"] {{
    border-color: {ACCENT}; background: {CAPTURE_BG}; color: {ACCENT_DIM};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ {image}width: 14px; height: 14px; margin-right: 6px; }}
QComboBox:disabled {{ color: {DIS_TEXT}; background: {DIS_BG}; }}
QComboBox QAbstractItemView {{
    background: {PANEL_HI}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM}; selection-color: {SEL_TEXT}; outline: none;
}}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent; padding: 6px 14px; margin-right: 4px;
    border-bottom: 2px solid transparent; color: {TEXT_DIM};
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QListWidget, QTableWidget, QTreeWidget {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 8px;
    outline: none;
}}
QListWidget::item {{ padding: 5px 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {ACCENT_DIM}; color: {SEL_TEXT}; }}
QListWidget::item:hover:!selected {{ background: {PANEL_HI}; }}
QListWidget::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {HOVER_BORDER}; background: {FIELD};
}}
QListWidget::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QListWidget#Cycle {{ background: {PANEL_HI}; }}
QListWidget#Cycle::item {{ color: {TEXT_DIM}; padding: 3px 8px; }}
QHeaderView::section {{
    background: {PANEL_HI}; border: none; border-bottom: 1px solid {BORDER};
    padding: 6px; color: {TEXT_DIM}; font-weight: 600;
}}
QTableWidget::item:selected {{ background: {ACCENT_DIM}; color: {SEL_TEXT}; }}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {HOVER_BORDER};
    background: {FIELD};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
}}
QCheckBox:disabled {{ color: {DIS_TEXT}; }}

QSlider::groove:horizontal {{ height: 4px; background: {TRACK}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
}}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SCROLL}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {SCROLL_HI}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {SCROLL}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}

/* Kafelek wciśniętego przycisku w zakładce Monitor. */
QFrame#PressIndicator {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 8px;
}}
QFrame#PressIndicator[active="true"] {{
    background: {ACCENT}; border: 1px solid {ACCENT_SOFT};
}}
QFrame#PressIndicator[active="true"] QLabel {{ color: #FFFFFF; }}

QFrame#ColorPickerPopup {{
    background: {PANEL}; border: 1px solid {HOVER_BORDER}; border-radius: 12px;
}}

QToolTip {{
    background: {TOOLTIP}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 5px; border-radius: 5px;
}}
QStatusBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; color: {TEXT_DIM}; }}
QStatusBar::item {{ border: none; }}
QSplitter::handle {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
"""


def _chevron_asset() -> str:
    """Rysuje strzałkę rozwijanej listy do pliku PNG (QSS nie umie rysować trójkątów)."""
    path = Path(tempfile.gettempdir()) / f"makkey_chevron_{_mode}.png"
    pm = QPixmap(14, 14)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(TEXT_DIM), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(3.5, 5.5), QPointF(7, 9))
    p.drawLine(QPointF(7, 9), QPointF(10.5, 5.5))
    p.end()
    pm.save(str(path), "PNG")
    return path.as_posix()


def stylesheet() -> str:
    """Arkusz stylów bieżącego motywu (wymaga istniejącej instancji QApplication)."""
    try:
        return _qss(_chevron_asset())
    except Exception:  # pragma: no cover - brak QGuiApplication
        return _qss("")


def make_icon(size: int = 64, active: bool = True) -> QIcon:
    """Ikona: sylwetka MAKKEY - obudowa, pasek OLED i matryca klawiszy."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    tile = QLinearGradient(0, 0, size, size)
    tile.setColorAt(0.0, QColor("#22262E"))
    tile.setColorAt(1.0, QColor("#12141A"))
    p.setBrush(QBrush(tile))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)

    s = size
    accent = QColor(ACCENT if active else "#5A6170")
    unit = s * 0.16
    gap = s * 0.045
    left = (s - (4 * unit + 3 * gap)) / 2
    top = s * 0.20

    # Górny rząd: przycisk 13 (akcent) i pasek wyświetlacza.
    p.setBrush(accent)
    p.drawRoundedRect(QRectF(left, top, unit, unit), unit * 0.22, unit * 0.22)
    p.setBrush(QColor("#0A0D12"))
    p.drawRoundedRect(
        QRectF(left + unit + gap, top + unit * 0.22, 3 * unit + 2 * gap, unit * 0.56),
        unit * 0.12, unit * 0.12,
    )

    # Matryca 4x3.
    p.setBrush(QColor("#454C58"))
    for r in range(3):
        for c in range(4):
            x = left + c * (unit + gap)
            y = top + (r + 1) * (unit + gap)
            p.drawRoundedRect(QRectF(x, y, unit, unit), unit * 0.22, unit * 0.22)

    p.end()
    return QIcon(pm)
