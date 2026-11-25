"""Główne okno MAKKEY - spina panel profili, podgląd urządzenia i zakładki."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTabWidget,
    QApplication, QMessageBox, QMenu, QSystemTrayIcon
)

from . import theme as T
from . import config as config_io
from . import i18n
from . import key_sender
from .config import AppConfig
from .constants import (
    APP_NAME, APP_VERSION, APP_WINDOW_TITLE, DEFAULT_CONFIG_PATH,
    PROFILE_BUTTON_INDEX, TOTAL_BUTTON_COUNT,
    ACTION_SHORTCUT, ACTION_TEXT, ACTION_MEDIA, ACTION_PROFILE,
)
from .i18n import tr
from .models import AppModel
from .app_watcher import ForegroundWatcher
from .updater import Updater, cleanup_old_exe, start_new_instance
from .device.hid_link import MakkeyLink, enumerate_hid_devices, to_oled_ascii
from .widgets.top_bar import TopBar
from .widgets.profile_panel import ProfilePanel
from .widgets.device_preview import DevicePreviewPanel
from .widgets.tab_keys import TabKeys
from .widgets.tab_device import TabDevice
from .widgets.tab_monitor import TabMonitor
from .widgets.tab_settings import TabSettings


class MainWindow(QMainWindow):
    # Okno bez rodzica żyje tak długo, jak trzyma je Python. Po zmianie języka
    # okno buduje się od nowa i ta referencja jest jedyną, jaką ma następca.
    current: MainWindow | None = None

    def __init__(self):
        super().__init__()
        first_window = MainWindow.current is None     # a nie następca po zmianie języka
        MainWindow.current = self

        # --- stan aplikacji ---
        self.cfg = AppConfig()
        self.model = AppModel()
        _, message, fields = config_io.load(self.cfg, self.model)
        # Język jest zapisany w konfiguracji - ustawiamy go, zanim powstanie
        # pierwszy widget z tekstem.
        self.cfg.language = i18n.set_language(self.cfg.language)
        load_message = tr(message, **fields)

        self._quitting = False          # wyjście z menu w zasobniku
        self._syncing_active = False    # przełącznik "Aktywny" jest w dwóch miejscach
        self._tray_hint_shown = False

        # Motyw musi stać zanim powstaną widgety - część z nich czyta kolory
        # już przy tworzeniu (kropki stanu, przełączniki).
        T.apply_mode(self.cfg.theme)
        T.apply_accent(self.cfg.accent)

        self.setWindowTitle(APP_WINDOW_TITLE)
        self.setWindowIcon(T.make_icon())
        self.resize(1380, 820)
        self.setMinimumSize(1080, 640)

        # --- aktualizacje z repozytorium (bez własnego widoku - patrz niżej) ---
        self.updater = Updater(self)
        self._update_info = None

        self._build_ui(load_message)
        self._build_tray()

        # --- łącze z urządzeniem ---
        self.link = MakkeyLink(self)
        self.link.enabled = self.cfg.active

        # --- automatyczny dobór profilu po programie na pierwszym planie ---
        self.app_watcher = ForegroundWatcher(self)

        self._connect_signals()
        self._restyle()
        self._apply_hardware()
        self._apply_active_state()
        self.profile_panel.set_manual_mode(self.model.manual_profile_switching)
        self._refresh_profile_views()

        # rejestracja raw inputu wymaga istniejącego HWND
        QTimer.singleShot(0, self._start_link)
        QTimer.singleShot(0, self.app_watcher.start)
        if first_window:
            # Chwilę po starcie: poprzednia instancja (po podmianie exe) zdąży
            # się zamknąć i zwolnić plik.
            QTimer.singleShot(5000, cleanup_old_exe)

        # zapis jest opóźniony, żeby nie pisać na dysk przy każdym znaku
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self._save_now)

    # ================================================================= UI ==
    def _build_ui(self, load_message: str):
        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 6)
        outer.setSpacing(8)

        self.top_bar = TopBar(theme_mode=self.cfg.theme, active=self.cfg.active)
        outer.addWidget(self.top_bar)

        middle = QHBoxLayout()
        middle.setSpacing(10)

        self.profile_panel = ProfilePanel(self.model)
        middle.addWidget(self.profile_panel, 0)

        self.preview_panel = DevicePreviewPanel(self.model)
        middle.addWidget(self.preview_panel, 0)

        self.tabs = QTabWidget()
        self.tab_keys = TabKeys(self.model)
        self.tab_device = TabDevice()
        self.tab_monitor = TabMonitor()
        self.tab_settings = TabSettings(self.cfg)
        self.tabs.addTab(self.tab_keys, tr("Przyciski"))
        self.tabs.addTab(self.tab_device, tr("Urządzenie"))
        self.tabs.addTab(self.tab_monitor, tr("Monitor"))
        self.tabs.addTab(self.tab_settings, tr("Ustawienia"))
        middle.addWidget(self.tabs, 1)

        outer.addLayout(middle, 1)
        self.setCentralWidget(root)

        self.status_action = QLabel(load_message)
        self.status_path = QLabel(str(config_io.get_config_path()))
        self.status_path.setObjectName("Hint")
        self.statusBar().addWidget(self.status_action, 1)
        self.statusBar().addPermanentWidget(self.status_path)

    # ---------------------------------------------------------------- tray --
    def _build_tray(self):
        """Ikona w zasobniku - program ma działać także po zamknięciu okna.

        Bez niej wyłączenie okna kończyło proces, a wtedy nic już nie odbiera
        raportów z macropada.
        """
        self.tray = QSystemTrayIcon(T.make_icon(active=self.cfg.active), self)

        menu = QMenu()
        act_show = QAction(tr("Pokaż okno"), self)
        act_show.triggered.connect(self._restore)
        self.act_active = QAction(tr("Aktywny"), self, checkable=True,
                                  checked=self.cfg.active)
        self.act_active.toggled.connect(self._on_active_toggled)
        act_quit = QAction(tr("Zakończ"), self)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_show)
        menu.addAction(self.act_active)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        # Menu żyje tylko tak długo, jak trzyma je Python - bez referencji
        # zostałoby zebrane zaraz po wyjściu z tej metody.
        self._tray_menu = menu

        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self._refresh_tray()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore()

    def _restore(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _refresh_tray(self):
        """Ikona i podpowiedź w tacce niosą stan - to jedyne, co widać po
        schowaniu okna."""
        self.tray.setIcon(T.make_icon(active=self.cfg.active))
        state = tr("aktywny") if self.cfg.active else tr("wstrzymany")
        self.tray.setToolTip(f"{APP_NAME} {APP_VERSION} - {state}")

    def _quit(self):
        """Wyjście z menu w zasobniku - pomija chowanie do tacki."""
        self._quitting = True
        self.close()

    # ------------------------------------------------------------- sygnały
    def _connect_signals(self):
        # wybór przycisku: podgląd <-> edytor
        self.preview_panel.buttonSelected.connect(self._on_button_selected)
        self.tab_keys.buttonSelected.connect(self.preview_panel.set_selected)

        # zmiany mapowań / kolorów / predefiniowania
        self.tab_keys.colorChanged.connect(self._on_color_changed)
        self.tab_keys.mappingChanged.connect(self._on_mapping_changed)
        self.tab_keys.commentChanged.connect(self._on_comment_changed)
        self.tab_keys.buttonEnabledChanged.connect(self._on_button_enabled_changed)

        # tryb przełączania profili
        self.tab_keys.manualSwitchingChanged.connect(self.profile_panel.set_manual_mode)
        self.tab_keys.manualSwitchingChanged.connect(self._on_manual_mode_changed)

        # wyświetlacz
        self.tab_keys.oledTestRequested.connect(self._on_oled_test)

        # profile
        self.profile_panel.profileChanged.connect(self._on_profile_changed)
        self.profile_panel.cycleChanged.connect(self.tab_keys.refresh_cycle_list)
        self.profile_panel.cycleChanged.connect(self._schedule_save)
        self.profile_panel.profilesChanged.connect(self._on_profiles_changed)
        self.profile_panel.profilesChanged.connect(self._schedule_save)
        self.app_watcher.appChanged.connect(self._on_foreground_app)

        # urządzenie
        self.tab_device.rescanRequested.connect(self._on_rescan)
        self.tab_device.pingRequested.connect(self._on_ping)

        # monitor
        self.tab_monitor.simulatePress.connect(self._on_simulated_press)

        # ustawienia
        self.tab_settings.settingsChanged.connect(self._schedule_save)
        self.tab_settings.hardwareChanged.connect(self._apply_hardware)
        self.tab_settings.accentChanged.connect(self._on_accent_changed)
        self.tab_settings.brightnessChanged.connect(self._on_brightness_changed)
        self.tab_settings.configPathChanged.connect(self._on_config_path_changed)
        self.tab_settings.languageChanged.connect(self._on_language_changed)
        self.tab_settings.exportRequested.connect(self._on_config_export)
        self.tab_settings.importRequested.connect(self._on_config_import)
        self.tab_settings.factoryResetRequested.connect(self._on_factory_reset)

        # aktualizacje
        self.updater.checkFinished.connect(self._on_update_checked)
        self.updater.checkFailed.connect(self._on_update_check_failed)
        self.updater.installProgress.connect(self._on_update_progress)
        self.updater.installFinished.connect(self._on_update_installed)
        self.updater.installFailed.connect(self._on_update_failed)

        # pasek górny
        self.top_bar.themeChanged.connect(self._on_theme_changed)
        self.top_bar.activeToggled.connect(self._on_active_toggled)

        # łącze HID
        self.link.buttonPressed.connect(self._on_device_press)
        self.link.buttonReleased.connect(self._on_device_release)
        self.link.deviceStateChanged.connect(self._on_device_state)
        self.link.rawEvent.connect(self.tab_monitor.append_raw)
        self.link.firmwareInfo.connect(self.tab_device.set_firmware)

    # --------------------------------------------------------- urządzenie
    def _start_link(self):
        app = QApplication.instance()
        app.installNativeEventFilter(self.link)
        if not self.link.start(int(self.winId())):
            self.status_action.setText(
                tr("Nie udało się zarejestrować odbioru z urządzenia (Raw Input).")
            )
        self._refresh_device_table()

    def _on_rescan(self):
        connected = self.link.rescan()
        self._refresh_device_table()
        self.status_action.setText(
            tr("Znaleziono urządzenie MAKKEY.") if connected else
            tr("Nie znaleziono urządzenia MAKKEY - sprawdź połączenie i firmware.")
        )

    def _on_ping(self):
        if not self.cfg.active:
            self.status_action.setText(
                tr("MAKKEY wstrzymany - włącz przełącznik \"Aktywny\", żeby wysłać PING.")
            )
        elif self.link.ping():
            self.status_action.setText(tr("Wysłano PING - czekam na odpowiedź."))
        else:
            self.status_action.setText(tr("Nie udało się wysłać PING (brak łącza)."))

    def _refresh_device_table(self):
        self.tab_device.set_devices(enumerate_hid_devices())

    def _on_device_state(self, connected: bool, name: str):
        self.top_bar.set_device_connected(connected, name)
        self.tab_device.set_device_state(
            connected, name, self.link.vid_pid, self.link.usage_text
        )
        if connected:
            # Świeżo podłączone urządzenie nie zna jeszcze bieżącego profilu.
            self._push_profile_to_device()

    def _on_device_press(self, index: int):
        self.preview_panel.show_press(index, hold_ms=0)   # 0 = trzymaj do puszczenia
        self.tab_keys.press(index, True)
        self.tab_monitor.log_press(index, self._action_text(index))
        self._run_action(index)

    def _run_action(self, index: int):
        """Wykonuje akcję przycisku z bieżącego profilu.

        Tylko dla prawdziwych naciśnięć - symulowane z Monitora wysłałyby
        skrót do okna MAKKEY, które ma wtedy fokus.
        """
        mapping = self.model.mapping(index)
        if not mapping.enabled:
            return
        if mapping.action_type == ACTION_PROFILE:
            # Działa także w wyłączonym profilu - inaczej nie dałoby się z niego wyjść.
            self._next_manual_profile()
            return
        if not self.model.current_profile.enabled or not mapping.value:
            return
        try:
            if mapping.action_type == ACTION_SHORTCUT:
                key_sender.send_shortcut(mapping.value)
            elif mapping.action_type == ACTION_TEXT:
                key_sender.type_text(mapping.value)
            elif mapping.action_type == ACTION_MEDIA:
                key_sender.send_media(mapping.value)
        except key_sender.KeySendError as exc:
            message = tr('Przycisk {n}: nie wysłano "{value}" - {error}',
                         n=index, value=mapping.describe(), error=exc)
            self.status_action.setText(message)
            self.tab_monitor.append_note(message)

    def _next_manual_profile(self):
        """Przycisk 13 w trybie ręcznym: następny włączony profil z cyklu."""
        if not self.model.manual_profile_switching:
            return   # tryb automatyczny - profil dobiera nazwa procesu
        cycle = [i for i, p in enumerate(self.model.profiles)
                 if p.in_manual_cycle and p.enabled]
        current = self.model.current_profile_index
        if not cycle or cycle == [current]:
            return
        target = (cycle[(cycle.index(current) + 1) % len(cycle)]
                  if current in cycle else cycle[0])
        self.profile_panel.load_profile(target)
        self._on_profile_changed(target)

    def _on_device_release(self, index: int):
        self.preview_panel.clear_press(index)
        self.tab_keys.press(index, False)
        self.tab_monitor.clear_press(index)

    def _on_simulated_press(self, index: int):
        self.preview_panel.show_press(index, hold_ms=450)
        self.tab_keys.press(index, True)
        self.tab_monitor.log_press(index, self._action_text(index))
        QTimer.singleShot(450, lambda: self._on_simulated_release(index))

    def _on_simulated_release(self, index: int):
        self.tab_keys.press(index, False)
        self.tab_monitor.clear_press(index)

    def _action_text(self, index: int) -> str:
        mapping = self.model.mapping(index)
        text = mapping.describe()
        if not mapping.enabled:
            text = tr("{action}  [wyłączony]", action=text)
        note = mapping.note()
        return f"{text}  ({note})" if note else text

    # ---------------------------------------------- wysyłka do urządzenia
    def _push_profile_to_device(self):
        """Komplet kolorów + nazwa profilu na wyświetlacz po zmianie profilu.

        Sprzęt odznaczony w Ustawieniach jest gaszony, a nie tylko pomijany -
        inaczej urządzenie świeciłoby dalej tym, co dostało ostatnio.
        """
        if not self.link.is_connected:
            return
        if self.cfg.has_leds:
            self.link.set_brightness(self.cfg.led_brightness)
            self.link.set_all_leds(self.model.colors())
        else:
            self.link.set_all_leds({})   # brak koloru = #000000 dla każdej diody
        self._push_oled()

    def _push_oled(self):
        """Wyświetlacz pokazuje zawsze nazwę aktywnego profilu."""
        if not self.link.is_connected:
            return
        if self.cfg.has_oled:
            self.link.oled_text(0, self.model.current_profile.name)
        else:
            self.link.oled_clear()

    # -------------------------------------------------------------- edycja
    def _on_button_selected(self, index: int):
        self.tab_keys.load_button(index)
        self.preview_panel.set_selected(index)
        self.tabs.setCurrentWidget(self.tab_keys)

    def _on_color_changed(self, index: int, color: str):
        self.preview_panel.set_color(index, color)
        if self.cfg.has_leds:
            self.link.set_led(index, color)
        self._schedule_save()

    def _on_mapping_changed(self, index: int):
        self.preview_panel.refresh()
        self._refresh_monitor_captions()
        self.status_action.setText(tr(
            "Przycisk {n}: {action}", n=index, action=self.model.mapping(index).describe()
        ))
        self._schedule_save()

    def _on_comment_changed(self, _index: int):
        """Komentarz to sama notatka - tylko podgląd i zapis, bez urządzenia."""
        self.preview_panel.refresh()
        self._schedule_save()

    def _on_button_enabled_changed(self, index: int, enabled: bool):
        self.preview_panel.set_button_enabled(index, enabled)
        self._refresh_monitor_captions()
        name = (tr("Przycisk 13 (zmiana profilu)") if index == PROFILE_BUTTON_INDEX
                else tr("Przycisk {n}", n=index))
        template = ('{button}: predefiniowanie włączone w profilu "{profile}"' if enabled
                    else '{button}: predefiniowanie wyłączone w profilu "{profile}"')
        self.status_action.setText(
            tr(template, button=name, profile=self.model.current_profile.name)
        )
        self._schedule_save()

    def _on_profile_changed(self, _index: int):
        self._refresh_profile_views()
        self._push_profile_to_device()
        self.status_action.setText(
            tr("Aktywny profil: {name}", name=self.model.current_profile.name)
        )
        self._schedule_save()

    def _on_profiles_changed(self):
        """Zmiana nazwy aktywnego profilu musi od razu trafić na wyświetlacz."""
        name = self.model.current_profile.name
        self.preview_panel.set_oled_text(name)
        self.tab_keys.set_oled_preview(name)
        if self.cfg.has_oled:
            self._push_oled()

    def _on_foreground_app(self, exe: str):
        """Tryb automatyczny: profil dobierany po programie na pierwszym planie."""
        if self.model.manual_profile_switching:
            return
        target = self.model.profile_for_exe(exe)
        if target is None or target == self.model.current_profile_index:
            return
        self.profile_panel.load_profile(target)
        self._refresh_profile_views()
        self._push_profile_to_device()
        self.status_action.setText(tr(
            "Aktywny profil: {name} (program: {exe})",
            name=self.model.current_profile.name, exe=exe,
        ))
        # Bez zapisu - przy każdej zmianie okna pisalibyśmy na dysk, a po
        # starcie profil i tak dobierze się na nowo.

    def _refresh_profile_views(self):
        self.tab_keys.refresh_profile()
        self.preview_panel.refresh()
        self._refresh_monitor_captions()

    def _refresh_monitor_captions(self):
        self.tab_monitor.set_captions({
            i: self.model.mapping(i).describe() for i in range(1, TOTAL_BUTTON_COUNT + 1)
        })

    def _on_manual_mode_changed(self, manual: bool):
        self.status_action.setText(
            tr("Przełączanie profili: ręczne (przycisk 13)") if manual
            else tr("Przełączanie profili: automatyczne (po nazwie .exe)")
        )
        self._schedule_save()

    # ---------------------------------------------------------- wyświetlacz
    def _on_oled_test(self):
        target = self.model.current_profile.name
        self.preview_panel.set_oled_text(target)
        if not self.cfg.active:
            self.status_action.setText(
                tr("MAKKEY wstrzymany - OLED zmieniony tylko w podglądzie.")
            )
        elif self.link.oled_text(0, target):
            self.status_action.setText(tr('Wysłano na OLED: "{text}"',
                                          text=to_oled_ascii(target)))
        else:
            self.status_action.setText(
                tr("Brak łącza z urządzeniem - OLED tylko w podglądzie.")
            )

    # ---------------------------------------------------------- ustawienia
    def _apply_hardware(self):
        """Wariant sprzętowy: bez diod / bez wyświetlacza znikają całe sekcje."""
        leds, oled = self.cfg.has_leds, self.cfg.has_oled
        self.tab_keys.set_hardware(leds, oled)
        self.preview_panel.set_hardware(leds, oled)
        if self.link.is_connected:
            self._push_profile_to_device()

    def _on_brightness_changed(self, value: int):
        if self.cfg.has_leds:
            self.link.set_brightness(value)

    def _on_accent_changed(self, code: str):
        T.apply_accent(code)
        self._restyle()
        self._schedule_save()

    def _on_theme_changed(self, mode: str):
        self.cfg.theme = T.apply_mode(mode)
        self._restyle()
        self._schedule_save()

    def _restyle(self):
        """Nadaje aplikacji nowy arkusz stylów i odświeża to, co trzyma kolory."""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(T.stylesheet())
            app.setWindowIcon(T.make_icon())
        self.setWindowIcon(T.make_icon())
        self._refresh_tray()          # ikona w tacce też jest w kolorze wiodącym
        self.top_bar.set_theme_mode(T.mode())
        self.top_bar.refresh_device_state()
        self.preview_panel.repaint_dot()
        self.preview_panel.macropad.update()
        self.tab_keys.macropad.update()

    def _on_active_toggled(self, active: bool):
        # Ten sam przełącznik stoi w pasku górnym i w menu zasobnika - bez
        # blokady ustawianie jednego odbijałoby się w drugim w kółko.
        if self._syncing_active:
            return
        self._syncing_active = True
        try:
            self.cfg.active = active
            self.top_bar.active_switch.setChecked(active)
            self.act_active.setChecked(active)
        finally:
            self._syncing_active = False
        self._apply_active_state()
        self._schedule_save()
        self.status_action.setText(
            tr("MAKKEY aktywny - odbiera przyciski i steruje urządzeniem") if active
            else tr("MAKKEY wstrzymany - nie odbiera przycisków i nie steruje urządzeniem")
        )

    def _apply_active_state(self):
        """Rozprowadza stan przełącznika "Aktywny" po całym programie."""
        active = self.cfg.active
        # Ustawienie łącza jako pierwsze: przy wyłączaniu zgłasza ono puszczenie
        # klawiszy trzymanych w tej chwili, żeby nie zostały zapalone na stałe.
        self.link.enabled = active
        self.top_bar.set_active(active)
        self.preview_panel.set_active(active)
        self.tab_keys.macropad.set_active(active)
        self._refresh_tray()
        if active:
            # Po wznowieniu urządzenie nie zna kolorów - trzeba je wysłać na nowo.
            self._push_profile_to_device()

    def _on_config_path_changed(self, new_path: str):
        target = Path(new_path)
        try:
            config_io.save(self.cfg, self.model, target)
            if target == DEFAULT_CONFIG_PATH:
                config_io.reset_config_path()
            else:
                config_io.set_config_path(target)
        except OSError as exc:
            QMessageBox.warning(
                self, "MAKKEY",
                tr("Nie udało się zapisać konfiguracji:\n{error}", error=exc),
            )
            self.tab_settings.load_from_config()
            return
        self.status_path.setText(str(target))
        self.status_action.setText(tr("Zapisano konfigurację w {path}", path=target))

    def _on_language_changed(self, code: str):
        """Nowy język = okno zbudowane od nowa (patrz _rebuild)."""
        self.cfg.language = code
        self._rebuild()

    def _rebuild(self, save: bool = True) -> MainWindow:
        """Stawia nowe okno w miejsce tego - ta sama pozycja i zakładka.

        Widgety dostają teksty i stan przy tworzeniu, więc zamiast odświeżać
        każdy z osobna zapisujemy stan i stawiamy nowe okno w tym samym
        procesie - wczytuje ono konfigurację dokładnie tak jak przy starcie.
        Restart procesu odpada: exe z PyInstallera --onefile uruchomiony przez
        samego siebie dzieli z rodzicem katalog tymczasowy, który ten zaraz
        kasuje.

        `save=False`, gdy w pliku leży już nowa konfiguracja (import,
        ustawienia fabryczne), której stan tego okna nie może nadpisać.
        """
        tab = self.tabs.currentIndex()
        geometry = self.saveGeometry()
        visible = self.isVisible()
        # Najpierw sprzątanie starego okna: zwalnia Raw Input i hak okien,
        # które następca zarejestruje na siebie.
        self._shutdown(save=save)

        successor = MainWindow()
        successor.restoreGeometry(geometry)
        successor.tabs.setCurrentIndex(tab)
        if visible:
            successor.show()
        self.hide()
        self.deleteLater()
        return successor

    # ------------------------------------- eksport / import / fabryczne
    def _on_config_export(self, path: str):
        """Kopia bieżącej konfiguracji w pliku wybranym przez użytkownika.

        Zapis idzie prosto ze stanu w pamięci, więc obejmuje także zmiany
        czekające jeszcze na opóźniony zapis. Lokalizacja config.json zostaje
        bez zmian.
        """
        target = Path(path)
        try:
            config_io.save(self.cfg, self.model, target)
        except OSError as exc:
            QMessageBox.warning(
                self, APP_NAME,
                tr("Nie udało się wyeksportować konfiguracji:\n{error}", error=exc),
            )
            return
        self.status_action.setText(tr("Wyeksportowano konfigurację do {path}", path=target))

    def _on_config_import(self, path: str):
        source = Path(path)
        # Plik sprawdzany jest przed pytaniem - nie ma sensu potwierdzać
        # podmiany, która i tak by się nie udała.
        try:
            cfg, model = config_io.import_config(source)
        except config_io.ConfigError as exc:
            QMessageBox.warning(self, APP_NAME, tr(exc.template, **exc.fields))
            return
        answer = QMessageBox.question(
            self, APP_NAME,
            tr("Zaimportować konfigurację z pliku {name}?\n\n"
               "Bieżące ustawienia, profile, przypisania przycisków i kolory "
               "zostaną zastąpione zawartością pliku.", name=source.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._replace_config(cfg, model, "Zaimportowano konfigurację z {path}", path=source)

    def _on_factory_reset(self):
        answer = QMessageBox.question(
            self, APP_NAME,
            tr("Przywrócić ustawienia fabryczne?\n\n"
               "Wszystkie ustawienia (także język i wariant urządzenia), profile, "
               "przypisania przycisków i kolory wrócą do wartości domyślnych. "
               "Tego nie da się cofnąć - jeśli chcesz zachować obecną "
               "konfigurację, najpierw ją wyeksportuj."),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._replace_config(AppConfig(), AppModel(), "Przywrócono ustawienia fabryczne.")

    def _replace_config(self, cfg: AppConfig, model: AppModel, message: str, **fields):
        """Podmienia całą konfigurację (import, ustawienia fabryczne).

        Nowa zawartość trafia do bieżącego pliku konfiguracyjnego, a okno
        buduje się od nowa i wczytuje ją jak przy starcie - zmienić się może
        wszystko naraz: język, motyw, wariant sprzętu, profile. `message` to
        nieprzetłumaczony szablon: tłumaczy go już następca, w języku nowej
        konfiguracji.
        """
        self._save_timer.stop()
        try:
            config_io.save(cfg, model)
        except OSError as exc:
            QMessageBox.warning(
                self, APP_NAME,
                tr("Nie udało się zapisać konfiguracji:\n{error}", error=exc),
            )
            return
        successor = self._rebuild(save=False)
        successor.status_action.setText(tr(message, **fields))

    # --------------------------------------------------------- aktualizacje
    # Program nie ma widoku aktualizacji (sekcji w Ustawieniach, dymków,
    # okien) i sam ich nie uruchamia. Logika zostaje gotowa do podpięcia:
    # _check_updates() -> _install_update() -> _restart_app(); stan trafia
    # tylko do paska stanu.
    def _check_updates(self):
        if self.updater.check():
            self.status_action.setText(tr("Sprawdzanie aktualizacji..."))

    def _on_update_checked(self, info):
        self._update_info = info
        if info.available:
            self.status_action.setText(tr("Dostępna aktualizacja: {latest} (masz {current}).",
                                          latest=info.latest, current=info.current))
        else:
            self.status_action.setText(tr("Masz najnowszą wersję ({version}).",
                                          version=info.current))

    def _on_update_check_failed(self, message: str):
        self.status_action.setText(
            tr("Nie udało się sprawdzić aktualizacji: {error}", error=message)
        )

    def _install_update(self):
        if self._update_info is None or not self._update_info.available:
            return
        if self.updater.install(self._update_info):
            self.status_action.setText(tr("Aktualizowanie..."))

    def _on_update_progress(self, done: int, total: int):
        mb = 1_048_576
        self.status_action.setText(
            tr("Pobieranie: {done:.1f} / {total:.1f} MB", done=done / mb, total=total / mb)
            if total else tr("Pobieranie: {done:.1f} MB", done=done / mb)
        )

    def _on_update_installed(self):
        self._update_info = None
        self.status_action.setText(
            tr("Aktualizacja zainstalowana - zadziała po ponownym uruchomieniu programu.")
        )

    def _on_update_failed(self, message: str):
        self.status_action.setText(tr("Aktualizacja nie powiodła się: {error}", error=message))

    def _restart_app(self):
        """Nowy proces z nowym kodem, ten się zamyka."""
        # Następca wczytuje config.json przy starcie - musi już być aktualny.
        self._save_timer.stop()
        try:
            config_io.save(self.cfg, self.model)
        except OSError:
            pass
        try:
            start_new_instance()
        except OSError as exc:
            self.status_action.setText(
                tr("Nie udało się uruchomić programu ponownie: {error}", error=exc)
            )
            return
        self._quit()

    # --------------------------------------------------------------- zapis
    def _schedule_save(self):
        self._save_timer.start()

    def _save_now(self):
        try:
            path = config_io.save(self.cfg, self.model)
        except OSError as exc:
            self.status_action.setText(tr("Błąd zapisu konfiguracji: {error}", error=exc))
            return
        self.status_action.setText(tr("Zapisano konfigurację ({name})", name=path.name))

    def closeEvent(self, event):
        # Zamknięcie okna chowa program do zasobnika - macropad ma działać
        # dalej. Realne wyjście idzie przez "Zakończ" w menu ikony albo gdy
        # chowanie jest wyłączone w Ustawieniach.
        if (self.cfg.minimize_to_tray and not self._quitting
                and self.tray.isVisible()):
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self.tray.showMessage(
                    APP_NAME,
                    tr("Działa dalej w tle. Kliknij ikonę w zasobniku, żeby wrócić."),
                    QSystemTrayIcon.Information, 3000,
                )
                self._tray_hint_shown = True
            return

        self._shutdown()
        event.accept()
        QApplication.instance().quit()

    def _shutdown(self, save: bool = True):
        if self._save_timer.isActive():
            self._save_timer.stop()
        if save:
            try:
                config_io.save(self.cfg, self.model)
            except OSError:
                pass
        self.app_watcher.stop()
        QApplication.instance().removeNativeEventFilter(self.link)
        self.link.stop()
        self.tray.hide()
