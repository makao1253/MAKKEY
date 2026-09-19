"""Interaktywny, rysowany widok urządzenia MAKKEY.

Stylistyka wzorowana na renderach z examples/ (macropad_*.jpg):
ciemna, aluminiowa obudowa z frezowanym rantem, keycapy z lekkim 3D
i kolorowa poświata LED (WS2812B) wydobywająca się spod klawiszy.

Układ:
    [13] [ ---- OLED 0.91" ---- ]
    [ 1] [ 2] [ 3] [ 4]
    [ 5] [ 6] [ 7] [ 8]
    [ 9] [10] [11] [12]

Widget pełni cztery role naraz:
  * selektor - klik w klawisz zaznacza go (pierścień w kolorze wiodącym)
    i przełącza edytor,
  * podgląd kolorów LED przypisanych w bieżącym profilu,
  * podgląd na żywo - klawisz fizycznie wciśnięty na urządzeniu rozjaśnia
    się i dostaje mocniejszy glow,
  * wskaźnik predefiniowania - kropka w lewym górnym rogu klawisza:
    zielona = akcja przycisku działa, czerwona = wyłączona w tym profilu.

Wariant sprzętowy (podświetlenie / wyświetlacz) ustawia `set_hardware()`:
bez diod nie rysujemy poświaty, bez wyświetlacza nie rysujemy ekranu.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QLinearGradient, QRadialGradient
)
from PySide6.QtWidgets import QWidget, QSizePolicy

from .. import theme as T
from ..i18n import tr
from ..constants import (
    GRID_COLUMNS, GRID_ROWS, PROFILE_BUTTON_INDEX,
    TOTAL_BUTTON_COUNT, DEFAULT_LED_COLOR,
)

# --- kolory obudowy (celowo takie same w obu motywach: to fizyczny
#     przedmiot, a nie element interfejsu) ---
CASE_TOP = QColor("#3a3a40")
CASE_BOTTOM = QColor("#141417")
CASE_RIM = QColor("#6e6e78")
WELL_COLOR = QColor("#0d0d0f")
KEYCAP_TOP = QColor("#4a4a52")
KEYCAP_BOTTOM = QColor("#2a2a30")
KEYCAP_EDGE = QColor("#15151a")


class MacropadWidget(QWidget):
    buttonSelected = Signal(int)   # klik myszą w klawisz (1..13)

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self.compact = compact
        min_w, min_h = (260, 210) if compact else (300, 320)
        self.setMinimumSize(min_w, min_h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

        self.selected: int = 1
        self.pressed: set[int] = set()
        self.hovered: int | None = None
        self.colors: dict[int, str] = {i: DEFAULT_LED_COLOR
                                       for i in range(1, TOTAL_BUTTON_COUNT + 1)}
        self.button_enabled: dict[int, bool] = {i: True
                                                for i in range(1, TOTAL_BUTTON_COUNT + 1)}
        self.oled_text: str = "MAKKEY"
        self.leds_enabled: bool = True
        self.oled_enabled: bool = True
        # False = MAKKEY wstrzymany przełącznikiem "Aktywny": urządzenie jest
        # rysowane wygaszone, bo program niczym nim nie steruje.
        self.device_active: bool = True

        self._rects: dict[int, QRectF] = {}
        self._oled_rect = QRectF()
        self._unit = 1.0
        self._case_rect = QRectF()

    # ------------------------------------------------------------------ API
    def set_colors(self, colors: dict[int, str]):
        self.colors.update(colors)
        self.update()

    def set_color(self, index: int, color: str):
        self.colors[index] = color
        self.update()

    def set_enabled_flags(self, flags: dict[int, bool]):
        self.button_enabled.update(flags)
        self.update()

    def set_button_enabled(self, index: int, enabled: bool):
        self.button_enabled[index] = enabled
        self.update()

    def set_hardware(self, leds: bool, oled: bool):
        """Wariant sprzętowy: czy urządzenie ma podświetlenie i wyświetlacz."""
        self.leds_enabled = leds
        self.oled_enabled = oled
        self.update()

    def set_active(self, on: bool):
        """Stan przełącznika "Aktywny" - wstrzymany MAKKEY gasi urządzenie."""
        if on != self.device_active:
            self.device_active = on
            self.update()

    def set_selected(self, index: int):
        self.selected = index
        self.update()

    def set_pressed(self, indices: set[int]):
        self.pressed = set(indices)
        self.update()

    def press(self, index: int, is_pressed: bool):
        if is_pressed:
            self.pressed.add(index)
        else:
            self.pressed.discard(index)
        self.update()

    def set_oled_text(self, text: str):
        self.oled_text = text
        self.update()

    # -------------------------------------------------------------- geometria
    def _compute_layout(self):
        """Wylicza prostokąty klawiszy zachowując proporcje urządzenia."""
        # jednostki w "rozmiarach klawisza"
        gap = 0.14
        pad = 0.42          # margines obudowy wokół pola klawiszy
        cols, rows = GRID_COLUMNS, GRID_ROWS + 1   # +1 na rząd z 13 i OLED

        units_w = cols + gap * (cols - 1) + pad * 2
        units_h = rows + gap * (rows - 1) + pad * 2

        margin = 12 if not self.compact else 8
        avail_w = self.width() - margin * 2
        avail_h = self.height() - margin * 2
        unit = max(8.0, min(avail_w / units_w, avail_h / units_h))

        case_w = units_w * unit
        case_h = units_h * unit
        case_x = (self.width() - case_w) / 2
        case_y = (self.height() - case_h) / 2
        self._case_rect = QRectF(case_x, case_y, case_w, case_h)

        origin_x = case_x + pad * unit
        origin_y = case_y + pad * unit
        step = unit * (1 + gap)

        self._rects.clear()
        # rząd górny: przycisk 13 nad przyciskiem 1, OLED po jego prawej
        self._rects[PROFILE_BUTTON_INDEX] = QRectF(origin_x, origin_y, unit, unit)
        oled_x = origin_x + step
        oled_w = 3 * unit + 2 * gap * unit
        # OLED 0.91" ma proporcje 128x32 -> spłaszczony, wyśrodkowany w pionie
        oled_h = min(unit * 0.62, oled_w * 32 / 128 * 1.9)
        self._oled_rect = QRectF(oled_x, origin_y + (unit - oled_h) / 2, oled_w, oled_h)

        # matryca 4x3
        idx = 1
        for r in range(GRID_ROWS):
            for c in range(GRID_COLUMNS):
                x = origin_x + c * step
                y = origin_y + (r + 1) * step
                self._rects[idx] = QRectF(x, y, unit, unit)
                idx += 1

        self._unit = unit

    # ------------------------------------------------------------- rysowanie
    def paintEvent(self, _event):
        self._compute_layout()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        self._draw_case(p)

        for index, rect in self._rects.items():
            self._draw_key(p, index, rect)

        if self.oled_enabled:
            self._draw_oled(p)

        if not self.device_active:
            self._draw_paused(p)

    def _draw_paused(self, p: QPainter):
        """Przygaszenie całego urządzenia + podpis - żeby wstrzymanie było
        widać z drugiego końca pokoju, a nie tylko w pasku stanu."""
        radius = self._unit * 0.28
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRoundedRect(self._case_rect, radius, radius)

        font = QFont()
        font.setPointSizeF(max(7.5, self._unit * 0.22))
        font.setBold(True)
        font.setLetterSpacing(QFont.PercentageSpacing, 115)
        p.setFont(font)
        p.setPen(QColor(T.WARN))
        label = self._case_rect.adjusted(0, 0, 0, -self._unit * 0.10)
        p.drawText(label, Qt.AlignHCenter | Qt.AlignBottom, tr("WSTRZYMANY"))

    def _draw_case(self, p: QPainter):
        rect = self._case_rect
        radius = self._unit * 0.28

        # cień pod urządzeniem
        shadow = QRectF(rect).adjusted(6, 10, 6, 14)
        grad_shadow = QRadialGradient(shadow.center(), shadow.width() * 0.7)
        grad_shadow.setColorAt(0.0, QColor(0, 0, 0, 110))
        grad_shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(grad_shadow)
        p.drawRoundedRect(shadow, radius, radius)

        # korpus - pionowy gradient jak szczotkowane aluminium
        body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        body.setColorAt(0.0, CASE_TOP)
        body.setColorAt(0.55, QColor("#232328"))
        body.setColorAt(1.0, CASE_BOTTOM)
        p.setBrush(body)
        p.setPen(QPen(CASE_RIM, 1.4))
        p.drawRoundedRect(rect, radius, radius)

        # wewnętrzne, zagłębione pole klawiszy
        well = rect.adjusted(self._unit * 0.16, self._unit * 0.16,
                             -self._unit * 0.16, -self._unit * 0.16)
        p.setBrush(WELL_COLOR)
        p.setPen(QPen(QColor(0, 0, 0, 140), 1))
        p.drawRoundedRect(well, radius * 0.7, radius * 0.7)

    def _draw_key(self, p: QPainter, index: int, rect: QRectF):
        is_pressed = index in self.pressed
        is_selected = index == self.selected
        is_hovered = index == self.hovered
        color = QColor(self.colors.get(index, DEFAULT_LED_COLOR))

        # --- poświata LED spod klawisza ---
        # Wstrzymany program nie steruje diodami, więc urządzenie jest ciemne.
        leds_lit = self.leds_enabled and self.device_active
        if leds_lit:
            intensity = 1.0 if is_pressed else (0.7 if is_hovered else 0.5)
            self._draw_glow(p, rect, color, intensity)

            # świecąca "podkładka" - to ona daje wyraźny kolorowy rant
            # widoczny dookoła keycapa, jak na renderach urządzenia
            pad = QRectF(rect).adjusted(-1, -1, 1, 1)
            pad_color = QColor(color)
            pad_color.setAlpha(255 if is_pressed else 190)
            p.setPen(Qt.NoPen)
            p.setBrush(pad_color)
            p.drawRoundedRect(pad, rect.width() * 0.2, rect.width() * 0.2)

        # keycap wciśnięty = przesunięty w dół i minimalnie mniejszy
        cap = QRectF(rect).adjusted(
            rect.width() * 0.13, rect.height() * 0.13,
            -rect.width() * 0.13, -rect.height() * 0.10,
        )
        if is_pressed:
            cap.translate(0, rect.height() * 0.035)
            cap.setHeight(cap.height() * 0.94)

        radius = rect.width() * 0.16

        # --- cień / bok keycapa (efekt 3D) ---
        side = QRectF(cap).adjusted(0, cap.height() * 0.10, 0, cap.height() * 0.10)
        p.setPen(Qt.NoPen)
        p.setBrush(KEYCAP_EDGE)
        p.drawRoundedRect(side, radius, radius)

        # --- górna powierzchnia keycapa ---
        grad = QLinearGradient(cap.topLeft(), cap.bottomLeft())
        if is_pressed and leds_lit:
            grad.setColorAt(0.0, self._mix(KEYCAP_TOP, color, 0.45))
            grad.setColorAt(1.0, self._mix(KEYCAP_BOTTOM, color, 0.30))
        elif is_pressed:
            grad.setColorAt(0.0, KEYCAP_TOP.lighter(130))
            grad.setColorAt(1.0, KEYCAP_BOTTOM.lighter(120))
        else:
            grad.setColorAt(0.0, KEYCAP_TOP)
            grad.setColorAt(1.0, KEYCAP_BOTTOM)
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(cap, radius, radius)

        # delikatne rozjaśnienie górnej krawędzi
        highlight = QRectF(cap).adjusted(cap.width() * 0.12, cap.height() * 0.08,
                                         -cap.width() * 0.12, -cap.height() * 0.55)
        hl_grad = QLinearGradient(highlight.topLeft(), highlight.bottomLeft())
        hl_grad.setColorAt(0.0, QColor(255, 255, 255, 26))
        hl_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(hl_grad)
        p.drawRoundedRect(highlight, radius * 0.7, radius * 0.7)

        # --- obramowanie zaznaczenia / hover ---
        # Pierścień w kolorze wiodącym, rozjaśnionym - inaczej zniknąłby na
        # klawiszu, któremu przypisano dokładnie ten sam kolor diody.
        select_color = QColor(T.ACCENT).lighter(135)
        if is_selected:
            ring = QRectF(rect).adjusted(-4.5, -4.5, 4.5, 4.5)
            ring_radius = rect.width() * 0.26
            p.setBrush(Qt.NoBrush)
            halo = QColor(select_color)
            halo.setAlpha(80)
            p.setPen(QPen(halo, 7))
            p.drawRoundedRect(ring, ring_radius, ring_radius)
            p.setPen(QPen(select_color, 2.2))
            p.drawRoundedRect(ring, ring_radius, ring_radius)
        elif is_hovered:
            ring = QRectF(rect).adjusted(-3.5, -3.5, 3.5, 3.5)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 85), 1.6))
            p.drawRoundedRect(ring, rect.width() * 0.26, rect.width() * 0.26)

        # --- numer klawisza ---
        font = QFont()
        font.setPointSizeF(max(6.5, rect.height() * 0.20))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255) if is_pressed else QColor(235, 235, 240))
        p.drawText(cap, Qt.AlignCenter, str(index))

        self._draw_state_dot(p, index, cap)

    def _draw_state_dot(self, p: QPainter, index: int, cap: QRectF):
        """Kropka predefiniowania w lewym górnym rogu keycapa."""
        enabled = self.button_enabled.get(index, True)
        d = max(4.0, cap.width() * 0.17)
        center = QPointF(cap.left() + d * 0.95, cap.top() + d * 0.95)

        color = QColor(T.OK if enabled else T.BAD)
        halo = QColor(color)
        halo.setAlpha(70)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(center, d * 0.85, d * 0.85)
        p.setBrush(color)
        p.setPen(QPen(QColor(0, 0, 0, 150), 1))
        p.drawEllipse(center, d / 2, d / 2)

    def _draw_glow(self, p: QPainter, rect: QRectF, color: QColor, intensity: float):
        spread = rect.width() * 0.62
        area = QRectF(rect).adjusted(-spread, -spread, spread, spread)
        grad = QRadialGradient(rect.center(), area.width() / 2)
        inner = QColor(color)
        inner.setAlpha(int(200 * intensity))
        mid = QColor(color)
        mid.setAlpha(int(85 * intensity))
        outer = QColor(color)
        outer.setAlpha(0)
        grad.setColorAt(0.0, inner)
        grad.setColorAt(0.38, mid)
        grad.setColorAt(1.0, outer)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawEllipse(area)

    def _draw_oled(self, p: QPainter):
        rect = self._oled_rect
        radius = rect.height() * 0.16

        # bezel
        p.setPen(QPen(QColor("#4a4a52"), 1))
        p.setBrush(QColor("#0a0a0c"))
        p.drawRoundedRect(rect, radius, radius)

        # aktywna matryca (OLED 0.91" ma czarne tło i jasne piksele)
        screen = rect.adjusted(rect.width() * 0.02, rect.height() * 0.12,
                               -rect.width() * 0.02, -rect.height() * 0.12)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#000000"))
        p.drawRect(screen)

        text = (self.oled_text or "").strip()
        if text:
            font = QFont("Consolas")
            font.setPointSizeF(max(6.0, screen.height() * 0.52))
            font.setBold(True)
            p.setFont(font)
            # charakterystyczna niebieskawa biel pikseli SSD1306
            p.setPen(QColor("#d8ecff"))
            p.drawText(screen, Qt.AlignCenter, text)

    @staticmethod
    def _mix(a: QColor, b: QColor, t: float) -> QColor:
        return QColor(
            int(a.red() + (b.red() - a.red()) * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue() + (b.blue() - a.blue()) * t),
        )

    # ------------------------------------------------------------ interakcja
    def mousePressEvent(self, event):
        pos = event.position()
        for index, rect in self._rects.items():
            if rect.contains(pos):
                self.selected = index
                self.update()
                self.buttonSelected.emit(index)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position()
        hovered = None
        for index, rect in self._rects.items():
            if rect.contains(pos):
                hovered = index
                break
        if hovered != self.hovered:
            self.hovered = hovered
            self.update()

    def leaveEvent(self, _event):
        if self.hovered is not None:
            self.hovered = None
            self.update()
