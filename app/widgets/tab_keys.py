"""Zakładka "Przyciski" - macropad + edytor zaznaczonego przycisku.

Zamiast upychać 13 kart naraz (co rozjeżdżało układ), zakładka pokazuje
rysowany macropad, a pod nim ustawienia TEGO przycisku, który jest na nim
zaznaczony. Ten sam widok stoi w podglądzie na żywo, więc klawisz wybiera
się tak samo w obu miejscach.

Kolejność sekcji: Akcja -> Kolor diody LED -> Wyświetlacz OLED. Dwie ostatnie
znikają, gdy w Ustawieniach zaznaczono wariant bez diod / bez wyświetlacza.
Wyświetlacz pokazuje zawsze nazwę aktywnego profilu - sekcja OLED niczego
nie edytuje, tylko pokazuje, co jest na ekranie.

Listy rozwijane trzymają zapisywaną wartość (polski identyfikator z
constants.py) w itemData, a pokazują jej tłumaczenie - dlatego czytamy
currentData(), a nie currentText().
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame,
    QPushButton, QCheckBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QScrollArea, QComboBox,
)

from ..constants import (
    ACTION_NONE, ACTION_SHORTCUT, ACTION_TEXT, ACTION_MEDIA, ACTION_PROFILE,
    ACTION_TYPES_STANDARD, LED_PRESET_COLORS, PROFILE_BUTTON_INDEX,
    MAX_MANUAL_PROFILES, OLED_MAX_CHARS, OLED_WIDTH_PX, OLED_HEIGHT_PX,
    MEDIA_ACTIONS,
)
from ..device.hid_link import to_oled_ascii
from ..i18n import tr
from ..models import AppModel
from .common import Card, HotkeyEdit, combo, hint, label_row
from .color_picker import ColorPickerPopup
from .macropad import MacropadWidget
from .toggle_switch import ToggleSwitch

# Teksty tłumaczone przy wyświetlaniu (tr), bo moduł ładuje się przed
# ustawieniem języka.
ACTION_HINTS = {
    ACTION_NONE: "Przycisk nie wywołuje żadnej akcji w tym profilu.",
    ACTION_SHORTCUT: "Skrót wysyłany jednorazowo przy naciśnięciu przycisku.",
    ACTION_TEXT: "Podany tekst zostanie wpisany znak po znaku.",
    ACTION_MEDIA: "Sterowanie multimediami / systemem Windows.",
    ACTION_PROFILE: "Przycisk 13 przełącza profil - patrz przełącznik obok.",
}


def _fill(box: QComboBox, values: list[str]):
    """Wartość zapisywana w itemData, na liście jej tłumaczenie."""
    for value in values:
        box.addItem(tr(value), value)


def _select(box: QComboBox, value: str):
    index = box.findData(value)
    if index >= 0:
        box.setCurrentIndex(index)


class ColorSwatch(QPushButton):
    """Podgląd koloru; klik otwiera pełny wybór koloru."""

    colorPicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(42, 42)
        self.setCursor(Qt.PointingHandCursor)
        self._color = QColor(LED_PRESET_COLORS[0])
        self._popup: ColorPickerPopup | None = None
        self._refresh()
        self.clicked.connect(self._open_picker)

    def _refresh(self):
        self.setStyleSheet(
            f"background:{self._color.name()}; border-radius:10px;"
            f"border:2px solid rgba(255,255,255,45);"
        )

    def color_hex(self) -> str:
        return self._color.name().upper()

    def set_color(self, value: str):
        color = QColor(value)
        if color.isValid():
            self._color = color
            self._refresh()

    def _open_picker(self):
        popup = ColorPickerPopup(self.color_hex(), self)
        popup.colorChanged.connect(self._on_picked)
        self._popup = popup

        # popup pod próbką, przycięty do krawędzi ekranu
        popup.adjustSize()
        below = self.mapToGlobal(self.rect().bottomLeft())
        screen = self.screen().availableGeometry()
        x = max(screen.left() + 8, min(below.x(), screen.right() - popup.width() - 8))
        y = below.y() + 6
        if y + popup.height() > screen.bottom():
            y = self.mapToGlobal(self.rect().topLeft()).y() - popup.height() - 6
        popup.move(x, y)
        popup.show()

    def _on_picked(self, color_hex: str):
        self.set_color(color_hex)
        self.colorPicked.emit(color_hex)


class PresetColorButton(QPushButton):
    def __init__(self, color_hex: str, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color_hex)
        self.setStyleSheet(
            f"background:{color_hex}; border-radius:12px;"
            f"border:1px solid rgba(128,128,128,90);"
        )


class TabKeys(QWidget):
    """Macropad + edytor akcji, koloru i predefiniowania zaznaczonego przycisku."""

    colorChanged = Signal(int, str)          # (nr przycisku, #RRGGBB)
    mappingChanged = Signal(int)             # nr przycisku
    commentChanged = Signal(int)             # nr przycisku (notatka użytkownika)
    buttonSelected = Signal(int)             # zmiana wyboru na macropadzie
    buttonEnabledChanged = Signal(int, bool) # predefiniowanie wł/wył
    manualSwitchingChanged = Signal(bool)
    oledTestRequested = Signal()             # ponowna wysyłka nazwy profilu

    def __init__(self, model: AppModel, parent=None):
        super().__init__(parent)
        self.model = model
        self._loading = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        area = QScrollArea()
        area.setWidgetResizable(True)
        outer.addWidget(area)

        host = QWidget()
        area.setWidget(host)
        root = QVBoxLayout(host)
        root.setContentsMargins(0, 0, 6, 0)
        root.setSpacing(8)

        root.addWidget(self._build_macropad_card())
        root.addWidget(self._build_action_card())
        root.addWidget(self._build_color_card())
        root.addWidget(self._build_oled_card())
        root.addStretch(1)

        self.load_button(self.model.selected_button)

    # ------------------------------------------------------------- budowanie
    def _build_macropad_card(self) -> QWidget:
        card = Card(tr("Przyciski"))
        self.macropad = MacropadWidget(compact=True)
        self.macropad.setFixedHeight(232)
        self.macropad.set_tooltip_provider(self.model.button_tooltip)
        self.macropad.buttonSelected.connect(self._on_macropad_clicked)
        card.add(self.macropad)
        card.add(hint(tr("Kliknij klawisz, żeby przypisać mu akcję i kolor. "
                         "Kropka w rogu klawisza pokazuje, czy jego predefiniowanie "
                         "jest włączone w tym profilu.")))
        return card

    def _build_action_card(self) -> QWidget:
        card = Card()

        # --- nagłówek: numer przycisku + włącznik predefiniowania ---
        header = QFrame()
        header.setObjectName("KeyHeader")
        head_lay = QHBoxLayout(header)
        head_lay.setContentsMargins(12, 7, 12, 7)
        head_lay.setSpacing(12)

        self.header_number = QLabel("1")
        self.header_number.setObjectName("KeyNumber")
        head_lay.addWidget(self.header_number)

        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        self.header_title = QLabel(tr("Przycisk {n}", n=1))
        self.header_title.setObjectName("Big")
        self.header_subtitle = hint(tr("Wiersz {row}, kolumna {col}", row=1, col=1))
        text_box.addWidget(self.header_title)
        text_box.addWidget(self.header_subtitle)
        head_lay.addLayout(text_box)
        head_lay.addStretch(1)

        # Box wyłącza funkcję tego jednego przycisku, zostawiając jego
        # ustawienia nietknięte - i robi to osobno w każdym profilu.
        self.enabled_checkbox = QCheckBox(tr("Predefiniowanie"))
        self.enabled_checkbox.setToolTip(tr(
            "Wyłączony przycisk nie wywołuje żadnej akcji, ale zachowuje\n"
            "przypisanie i kolor. Ustawienie jest osobne dla każdego profilu."
        ))
        self.enabled_checkbox.setCursor(Qt.PointingHandCursor)
        self.enabled_checkbox.toggled.connect(self._on_enabled_toggled)
        head_lay.addWidget(self.enabled_checkbox)
        card.add(header)

        # --- typ akcji ---
        self.type_combo = combo(16)
        _fill(self.type_combo, ACTION_TYPES_STANDARD)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        card.add_layout(label_row(tr("Typ akcji"), self.type_combo))

        # --- wartość akcji (skrót / tekst / media) ---
        self.value_row = QWidget()
        value_layout = QHBoxLayout(self.value_row)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(8)
        self.value_label = QLabel(tr("Skrót"))
        self.value_label.setMinimumWidth(96)
        value_layout.addWidget(self.value_label)

        self.hotkey_edit = HotkeyEdit()
        self.hotkey_edit.hotkeyChanged.connect(self._on_value_changed)
        value_layout.addWidget(self.hotkey_edit, 1)

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText(tr("Tekst do wpisania..."))
        self.text_edit.textChanged.connect(self._on_value_changed)
        self.text_edit.hide()
        value_layout.addWidget(self.text_edit, 1)

        self.media_combo = combo(18)
        _fill(self.media_combo, MEDIA_ACTIONS)
        self.media_combo.currentIndexChanged.connect(self._on_value_changed)
        self.media_combo.hide()
        value_layout.addWidget(self.media_combo, 1)
        card.add(self.value_row)

        # --- komentarz: notatka użytkownika, osobna w każdym profilu ---
        # Zostaje edytowalny także przy wyłączonym predefiniowaniu - to opis,
        # a nie część akcji.
        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText(tr(
            "Do czego służy ten skrót w tym programie..."
        ))
        self.comment_edit.setToolTip(tr(
            "Twoja notatka do tego przycisku. Zapisywana osobno w każdym\n"
            "profilu, pokazywana w podglądzie i w dymku nad klawiszem.\n"
            "Nie jest wysyłana do urządzenia."
        ))
        self.comment_edit.setClearButtonEnabled(True)
        self.comment_edit.textChanged.connect(self._on_comment_changed)
        card.add_layout(label_row(tr("Komentarz"), self.comment_edit))

        # --- tryb profili + cykl ręczny (tylko przycisk 13) ---
        self.mode_container = QWidget()
        mode_layout = QVBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)

        switch_row = QHBoxLayout()
        switch_row.setContentsMargins(0, 0, 0, 0)
        switch_row.setSpacing(8)
        mode_label = QLabel(tr("Ręczne przełączanie"))
        mode_label.setMinimumWidth(96)
        switch_row.addWidget(mode_label)
        self.manual_switch = ToggleSwitch(checked=False)
        self.manual_switch.toggledState.connect(self._on_manual_toggled)
        switch_row.addWidget(self.manual_switch)
        switch_row.addStretch(1)
        self.cycle_badge = QLabel(f"0 / {MAX_MANUAL_PROFILES}")
        self.cycle_badge.setObjectName("Badge")
        switch_row.addWidget(self.cycle_badge)
        mode_layout.addLayout(switch_row)

        self.cycle_list = QListWidget()
        self.cycle_list.setObjectName("Cycle")
        self.cycle_list.setFixedHeight(26 * MAX_MANUAL_PROFILES + 8)
        self.cycle_list.setSelectionMode(QAbstractItemView.NoSelection)
        mode_layout.addWidget(self.cycle_list)
        mode_layout.addWidget(hint(tr(
            "Profile dodaje się do cyklu w panelu po lewej (maksymalnie {max}).",
            max=MAX_MANUAL_PROFILES,
        )))
        card.add(self.mode_container)

        self.action_hint = hint(tr(ACTION_HINTS[ACTION_NONE]))
        card.add(self.action_hint)
        return card

    def _build_color_card(self) -> QWidget:
        self.color_card = Card(tr("Kolor diody LED"))

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)

        self.swatch = ColorSwatch()
        self.swatch.colorPicked.connect(self._apply_color)
        top.addWidget(self.swatch)

        hex_box = QVBoxLayout()
        hex_box.setSpacing(2)
        hex_box.addWidget(QLabel(tr("Kolor (HEX)")))
        self.hex_edit = QLineEdit()
        self.hex_edit.setMaxLength(7)
        self.hex_edit.setFixedWidth(100)
        self.hex_edit.setObjectName("Mono")
        self.hex_edit.editingFinished.connect(self._on_hex_edited)
        hex_box.addWidget(self.hex_edit)
        top.addLayout(hex_box)

        presets_box = QVBoxLayout()
        presets_box.setSpacing(2)
        presets_box.addWidget(QLabel(tr("Szybki wybór")))
        presets_row = QHBoxLayout()
        presets_row.setSpacing(5)
        for color_hex in LED_PRESET_COLORS:
            btn = PresetColorButton(color_hex)
            btn.clicked.connect(lambda _=False, c=color_hex: self._apply_color(c))
            presets_row.addWidget(btn)
        presets_row.addStretch(1)
        presets_box.addLayout(presets_row)
        top.addLayout(presets_box, 1)

        self.color_card.add_layout(top)
        self.color_card.add(hint(tr(
            "Kolor zapisywany jest razem z profilem i wysyłany do urządzenia "
            "przy jego aktywacji. Zmiana jest widoczna na podglądzie od razu."
        )))
        return self.color_card

    def _build_oled_card(self) -> QWidget:
        self.oled_card = Card(tr('Wyświetlacz OLED 0.91" ({w}x{h})',
                                 w=OLED_WIDTH_PX, h=OLED_HEIGHT_PX))

        # Tylko do odczytu: tekst bierze się z nazwy profilu (panel po lewej).
        self.oled_view = QLineEdit()
        self.oled_view.setReadOnly(True)
        self.oled_view.setObjectName("Mono")
        self.oled_send = QPushButton(tr("Wyślij na OLED"))
        self.oled_send.setObjectName("Primary")
        self.oled_send.clicked.connect(lambda: self.oledTestRequested.emit())
        text_row = label_row(tr("Na ekranie"), self.oled_view)
        text_row.addWidget(self.oled_send)
        self.oled_card.add_layout(text_row)

        self.oled_card.add(hint(tr(
            "Wyświetlacz pokazuje nazwę aktywnego profilu fontem 11x18 - mieści "
            "się {n} znaków, dłuższa nazwa zostanie ucięta. Standardowy font "
            "SSD1306 nie ma polskich znaków - ogonki zostaną zamienione na "
            "odpowiedniki bez znaków diakrytycznych (ą→a, ł→l).",
            n=OLED_MAX_CHARS,
        )))
        return self.oled_card

    # --------------------------------------------------------------- logika
    def set_hardware(self, leds: bool, oled: bool):
        """Wariant sprzętowy z Ustawień - sekcje bez sprzętu po prostu znikają."""
        self.color_card.setVisible(leds)
        self.oled_card.setVisible(oled)
        self.macropad.set_hardware(leds, oled)

    def load_button(self, index: int):
        """Wczytuje do formularza ustawienia przycisku `index`."""
        self._loading = True
        self.model.selected_button = index
        mapping = self.model.mapping(index)
        is_profile_button = index == PROFILE_BUTTON_INDEX

        self.macropad.set_selected(index)
        self.header_number.setText(str(index))
        if is_profile_button:
            self.header_title.setText(tr("Przycisk 13 - zmiana profilu"))
            self.header_subtitle.setText(tr("Nad przyciskiem 1, obok wyświetlacza OLED"))
        else:
            self.header_title.setText(tr("Przycisk {n}", n=index))
            self.header_subtitle.setText(tr(
                "Wiersz {row}, kolumna {col}",
                row=(index - 1) // 4 + 1, col=(index - 1) % 4 + 1,
            ))

        self.enabled_checkbox.setChecked(mapping.enabled)

        # typ akcji: dla 13 zablokowany na "Zmiana profilu"
        self.type_combo.clear()
        if is_profile_button:
            _fill(self.type_combo, [ACTION_PROFILE])
            self.type_combo.setEnabled(False)
        else:
            _fill(self.type_combo, ACTION_TYPES_STANDARD)
            self.type_combo.setEnabled(True)
            _select(self.type_combo, mapping.action_type)

        self.mode_container.setVisible(is_profile_button)
        self.manual_switch.setChecked(self.model.manual_profile_switching)

        self.swatch.set_color(mapping.color)
        self.hex_edit.setText(mapping.color.upper())
        self.comment_edit.setText(mapping.comment)

        self._loading = False
        self._sync_value_widgets()
        self._sync_enabled_state()
        self.refresh_cycle_list()

    def refresh_profile(self):
        """Przeładowuje wszystko, co należy do profilu (po jego zmianie)."""
        self.macropad.set_colors(self.model.colors())
        self.macropad.set_enabled_flags(self.model.enabled_flags())
        self.set_oled_preview(self.model.current_profile.name)
        self.load_button(self.model.selected_button)

    def refresh_cycle_list(self):
        """Odświeża listę profili biorących udział w ręcznym cyklu."""
        self.cycle_list.clear()
        cycle = self.model.manual_cycle_profiles()
        for position, profile in enumerate(cycle, start=1):
            QListWidgetItem(f"{position}.  {profile.name}", self.cycle_list)
        if not cycle:
            item = QListWidgetItem(tr("Brak profili w cyklu ręcznym"))
            item.setFlags(Qt.NoItemFlags)
            self.cycle_list.addItem(item)

        count = len(cycle)
        self.cycle_badge.setText(f"{count} / {MAX_MANUAL_PROFILES}")
        self.cycle_badge.setObjectName(
            "BadgeFull" if count >= MAX_MANUAL_PROFILES else "Badge"
        )
        self.cycle_badge.style().unpolish(self.cycle_badge)
        self.cycle_badge.style().polish(self.cycle_badge)

        # w trybie automatycznym cykl jest tylko informacyjny
        self.cycle_list.setEnabled(self.model.manual_profile_switching)

    # --------------------------------------------------- podgląd na macropadzie
    def press(self, index: int, pressed: bool):
        self.macropad.press(index, pressed)

    def set_color_preview(self, index: int, color: str):
        self.macropad.set_color(index, color)

    def set_oled_preview(self, text: str):
        self.oled_view.setText(to_oled_ascii(text))
        self.macropad.set_oled_text(text)

    # -------------------------------------------------------------- wewnątrz
    def _current_action(self) -> str:
        return self.type_combo.currentData() or ACTION_NONE

    def _sync_value_widgets(self):
        action = self._current_action()
        mapping = self.model.mapping(self.model.selected_button)
        self.action_hint.setText(tr(ACTION_HINTS.get(action, "")))

        if action == ACTION_PROFILE:
            self.value_row.hide()
            return

        self.value_row.setVisible(action != ACTION_NONE)
        self.hotkey_edit.setVisible(action == ACTION_SHORTCUT)
        self.text_edit.setVisible(action == ACTION_TEXT)
        self.media_combo.setVisible(action == ACTION_MEDIA)

        self._loading = True
        if action == ACTION_MEDIA:
            self.value_label.setText(tr("Akcja"))
            _select(self.media_combo, mapping.value)
        elif action == ACTION_TEXT:
            self.value_label.setText(tr("Tekst"))
            self.text_edit.setText(mapping.value)
        else:
            self.value_label.setText(tr("Skrót"))
            self.hotkey_edit.setText(mapping.value)
        self._loading = False

    def _sync_enabled_state(self):
        """Wyłączony przycisk ma wyszarzony edytor - ustawienia zostają widoczne."""
        enabled = self.model.mapping(self.model.selected_button).enabled
        self.type_combo.setEnabled(enabled and self.model.selected_button != PROFILE_BUTTON_INDEX)
        self.value_row.setEnabled(enabled)
        self.mode_container.setEnabled(enabled)
        self.color_card.setEnabled(enabled)

    # ------------------------------------------------------------- zdarzenia
    def _on_macropad_clicked(self, index: int):
        self.load_button(index)
        self.buttonSelected.emit(index)

    def _on_enabled_toggled(self, checked: bool):
        if self._loading:
            return
        index = self.model.selected_button
        self.model.mapping(index).enabled = checked
        self.macropad.set_button_enabled(index, checked)
        self._sync_enabled_state()
        self.buttonEnabledChanged.emit(index, checked)

    def _on_type_changed(self, _index: int):
        if self._loading:
            return
        mapping = self.model.mapping(self.model.selected_button)
        mapping.action_type = self._current_action()
        # Lista mediów zawsze coś pokazuje - bez tego widoczna pozycja nie
        # byłaby zapisana, a wybranie jej ponownie nie zgłasza zmiany.
        mapping.value = MEDIA_ACTIONS[0] if mapping.action_type == ACTION_MEDIA else ""
        self._sync_value_widgets()
        self.mappingChanged.emit(self.model.selected_button)

    def _on_value_changed(self, _value=None):
        if self._loading:
            return
        action = self._current_action()
        mapping = self.model.mapping(self.model.selected_button)
        if action == ACTION_MEDIA:
            mapping.value = self.media_combo.currentData() or ""
        elif action == ACTION_TEXT:
            mapping.value = self.text_edit.text()
        else:
            mapping.value = self.hotkey_edit.text()
        self.mappingChanged.emit(self.model.selected_button)

    def _on_comment_changed(self, text: str):
        if self._loading:
            return
        index = self.model.selected_button
        self.model.mapping(index).comment = text
        self.commentChanged.emit(index)

    def _on_manual_toggled(self, enabled: bool):
        if self._loading:
            return
        self.model.manual_profile_switching = enabled
        self.refresh_cycle_list()
        self.manualSwitchingChanged.emit(enabled)

    def _on_hex_edited(self):
        color = QColor(self.hex_edit.text())
        if color.isValid():
            self._apply_color(color.name().upper())
        else:
            self.hex_edit.setText(self.swatch.color_hex())

    def _apply_color(self, color_hex: str):
        index = self.model.selected_button
        self.model.mapping(index).color = color_hex
        self.swatch.set_color(color_hex)
        self.hex_edit.setText(color_hex.upper())
        self.macropad.set_color(index, color_hex)
        self.colorChanged.emit(index, color_hex)
