"""Lewy panel: lista profili + ich ustawienia.

Dwa tryby doboru profilu (przełącznik znajduje się przy akcji przycisku 13):
  * automatyczny - profil dobierany po nazwie procesu z pola "Pliki .exe",
  * ręczny       - profil przełączany przyciskiem 13 w cyklu obejmującym
                   maksymalnie MAX_MANUAL_PROFILES pozycji.

Włącznik całego profilu siedzi w kwadraciku przy jego nazwie na liście -
tak jak w MAKMOUSE - żeby dało się go przestawić bez wchodzenia w ustawienia.
"""
from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QCheckBox, QMessageBox,
)

from ..constants import MAX_MANUAL_PROFILES
from ..i18n import tr
from ..models import AppModel, Profile
from .common import Card, hint, row


class ProfilePanel(QWidget):
    profileChanged = Signal(int)      # zmiana aktywnego profilu
    cycleChanged = Signal()           # zmiana składu cyklu ręcznego
    profilesChanged = Signal()        # dodanie / usunięcie / zmiana nazwy

    def __init__(self, model: AppModel, parent=None):
        super().__init__(parent)
        self.model = model
        self._loading = False
        self.setFixedWidth(248)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        card = Card(tr("Profile"))

        # Kwadracik przy nazwie włącza i wyłącza profil - bez wchodzenia w jego
        # ustawienia i bez osobnego pola pod listą.
        self.list_widget = QListWidget()
        self.list_widget.setToolTip(tr("Kwadracik przy nazwie włącza i wyłącza profil"))
        self.list_widget.setMinimumHeight(190)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        card.add(self.list_widget)

        self.add_btn = QPushButton(tr("Dodaj"))
        self.dup_btn = QPushButton(tr("Duplikuj"))
        self.del_btn = QPushButton(tr("Usuń"))
        self.del_btn.setObjectName("Danger")
        self.add_btn.clicked.connect(self._add_profile)
        self.dup_btn.clicked.connect(self._duplicate_profile)
        self.del_btn.clicked.connect(self._delete_profile)
        card.add_layout(row(self.add_btn, self.dup_btn, self.del_btn))

        card.add(QLabel(tr("Nazwa")))
        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_name_edited)
        card.add(self.name_edit)

        card.add(QLabel(tr("Pliki .exe (po przecinku)")))
        self.exe_edit = QLineEdit()
        self.exe_edit.setPlaceholderText(tr("np. Fusion360.exe, Fusion.exe"))
        self.exe_edit.textEdited.connect(self._on_exe_edited)
        card.add(self.exe_edit)

        self.exe_hint = hint(tr("Używane przy automatycznym doborze profilu."))
        card.add(self.exe_hint)

        self.default_checkbox = QCheckBox(tr("Profil domyślny"))
        self.default_checkbox.setToolTip(tr(
            "W trybie automatycznym działa we wszystkich programach,\n"
            "których nie wpisano w żadnym innym profilu."
        ))
        self.default_checkbox.toggled.connect(self._on_default_toggled)
        card.add(self.default_checkbox)

        cycle_row = QHBoxLayout()
        cycle_row.setContentsMargins(0, 0, 0, 0)
        cycle_row.setSpacing(6)
        self.cycle_checkbox = QCheckBox(tr("W cyklu ręcznym"))
        self.cycle_checkbox.toggled.connect(self._on_cycle_toggled)
        cycle_row.addWidget(self.cycle_checkbox)
        self.cycle_badge = QLabel(f"0 / {MAX_MANUAL_PROFILES}")
        self.cycle_badge.setObjectName("Badge")
        cycle_row.addWidget(self.cycle_badge)
        cycle_row.addStretch(1)
        card.add_layout(cycle_row)

        self.cycle_hint = hint("")
        card.add(self.cycle_hint)

        # Tryb doboru profilu pokazujemy tu tylko informacyjnie - zmienia się
        # go przełącznikiem przy akcji przycisku 13.
        self.mode_hint = hint("")
        card.add(self.mode_hint)

        outer.addWidget(card, 1)

        self.refresh_list()
        self.load_profile(self.model.current_profile_index)

    # ---------------------------------------------------------------- widok
    def refresh_list(self, select: int | None = None):
        self._loading = True
        target = select if select is not None else self.model.current_profile_index
        self.list_widget.clear()
        for profile in self.model.profiles:
            label = (tr("{name}  (domyślny)", name=profile.name)
                     if profile.is_default else profile.name)
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if profile.enabled else Qt.Unchecked)
            self._paint_item(item, profile.enabled)
            self.list_widget.addItem(item)
        self._loading = False
        if self.model.profiles:
            self.list_widget.setCurrentRow(
                max(0, min(target, len(self.model.profiles) - 1))
            )
        self._refresh_cycle_badge()

    @staticmethod
    def _paint_item(item: QListWidgetItem, enabled: bool):
        """Wyłączony profil jest wyszarzony - widać to bez czytania kwadracika."""
        item.setData(Qt.ForegroundRole, None if enabled else Qt.gray)

    def load_profile(self, index: int):
        self._loading = True
        self.model.current_profile_index = index
        profile = self.model.profiles[index]

        self.list_widget.setCurrentRow(index)
        self.name_edit.setText(profile.name)
        self.exe_edit.setText(profile.exe)
        self.default_checkbox.setChecked(profile.is_default)
        self.cycle_checkbox.setChecked(profile.in_manual_cycle)
        self._loading = False
        self._refresh_cycle_badge()

    def set_manual_mode(self, manual: bool):
        """Wywoływane, gdy przełącznik przy przycisku 13 zmienia tryb."""
        self.exe_edit.setEnabled(not manual)
        self.exe_hint.setText(
            tr("Nieużywane w trybie ręcznym - profil wybiera przycisk 13.")
            if manual else tr("Używane przy automatycznym doborze profilu.")
        )
        self.mode_hint.setText(
            tr("Tryb: ręczny (przycisk 13)") if manual
            else tr("Tryb: automatyczny (po nazwie .exe)")
        )
        self._refresh_cycle_badge()

    def _refresh_cycle_badge(self):
        count = self.model.manual_cycle_count()
        self.cycle_badge.setText(f"{count} / {MAX_MANUAL_PROFILES}")
        full = count >= MAX_MANUAL_PROFILES
        self.cycle_badge.setObjectName("BadgeFull" if full else "Badge")
        self.cycle_badge.style().unpolish(self.cycle_badge)
        self.cycle_badge.style().polish(self.cycle_badge)

        profile = self.model.current_profile
        # blokujemy dokładanie kolejnych profili po osiągnięciu limitu
        self.cycle_checkbox.setEnabled(profile.in_manual_cycle or not full)
        self.cycle_hint.setText(
            tr("Osiągnięto limit {max} profili w cyklu ręcznym.", max=MAX_MANUAL_PROFILES)
            if full and not profile.in_manual_cycle else ""
        )

    # ------------------------------------------------------------- zdarzenia
    def _on_row_changed(self, row_index: int):
        if self._loading or row_index < 0:
            return
        self.load_profile(row_index)
        self.profileChanged.emit(row_index)

    def _on_item_changed(self, item: QListWidgetItem):
        """Kwadracik przy nazwie profilu - włącznik całego profilu."""
        if self._loading:
            return
        index = self.list_widget.row(item)
        if not (0 <= index < len(self.model.profiles)):
            return
        profile = self.model.profiles[index]
        enabled = item.checkState() == Qt.Checked
        if enabled == profile.enabled:
            return
        profile.enabled = enabled
        self._loading = True   # zmiana koloru wywołałaby ten slot jeszcze raz
        try:
            self._paint_item(item, enabled)
        finally:
            self._loading = False
        self.profilesChanged.emit()

    def _on_name_edited(self, text: str):
        if self._loading:
            return
        self.model.current_profile.name = text
        current = self.list_widget.currentRow()
        self.refresh_list(current)
        self.cycleChanged.emit()
        self.profilesChanged.emit()

    def _on_exe_edited(self, text: str):
        if not self._loading:
            self.model.current_profile.exe = text
            self.profilesChanged.emit()

    def _on_default_toggled(self, checked: bool):
        if self._loading:
            return
        profile = self.model.current_profile
        if checked:
            for other in self.model.profiles:
                other.is_default = other is profile
        else:
            profile.is_default = False
            # Zawsze musi zostać jakiś profil awaryjny dla nieznanych programów.
            if not any(p.is_default for p in self.model.profiles):
                self.model.profiles[-1].is_default = True
        self.refresh_list(self.list_widget.currentRow())
        self.load_profile(self.model.current_profile_index)
        self.profilesChanged.emit()

    def _on_cycle_toggled(self, checked: bool):
        if self._loading:
            return
        if checked and not self.model.can_add_to_manual_cycle():
            self.cycle_checkbox.setChecked(False)
            return
        self.model.current_profile.in_manual_cycle = checked
        self._refresh_cycle_badge()
        self.cycleChanged.emit()

    # --------------------------------------------------------- lista profili
    def _add_profile(self):
        profile = Profile(name=self._unique_name(tr("Nowy profil")))
        self.model.profiles.append(profile)
        index = len(self.model.profiles) - 1
        self.refresh_list(index)
        self.load_profile(index)
        self.profileChanged.emit(index)
        self.profilesChanged.emit()

    def _duplicate_profile(self):
        source = self.model.current_profile
        clone = deepcopy(source)
        clone.name = self._unique_name(tr("{name} (kopia)", name=source.name))
        clone.is_default = False
        # Cykl ręczny ma twardy limit - kopia nie może go po cichu przekroczyć.
        clone.in_manual_cycle = source.in_manual_cycle and self.model.can_add_to_manual_cycle()
        self.model.profiles.append(clone)
        index = len(self.model.profiles) - 1
        self.refresh_list(index)
        self.load_profile(index)
        self.profileChanged.emit(index)
        self.profilesChanged.emit()

    def _delete_profile(self):
        if len(self.model.profiles) <= 1:
            QMessageBox.information(
                self, "MAKKEY", tr("Musi zostać przynajmniej jeden profil.")
            )
            return
        profile = self.model.current_profile
        answer = QMessageBox.question(
            self, "MAKKEY", tr('Usunąć profil "{name}"?', name=profile.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.model.profiles.remove(profile)
        if not any(p.is_default for p in self.model.profiles):
            self.model.profiles[0].is_default = True
        index = min(self.model.current_profile_index, len(self.model.profiles) - 1)
        self.model.current_profile_index = index
        self.refresh_list(index)
        self.load_profile(index)
        self.profileChanged.emit(index)
        self.cycleChanged.emit()
        self.profilesChanged.emit()

    def _unique_name(self, base: str) -> str:
        names = {p.name for p in self.model.profiles}
        if base not in names:
            return base
        n = 2
        while f"{base} {n}" in names:
            n += 1
        return f"{base} {n}"
