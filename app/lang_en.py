"""Tłumaczenie angielskie: polski oryginał -> tekst angielski.

Klucze muszą być dokładnie takie jak w wywołaniach tr() (razem ze
spacjami, cudzysłowami i znakami nowej linii), a pola w nawiasach
klamrowych - takie same po obu stronach.
"""
from __future__ import annotations

EN: dict[str, str] = {
    # --- typy akcji i media (wartości zapisywane w config.json) ---
    "Brak akcji": "No action",
    "Skrót klawiszowy": "Keyboard shortcut",
    "Wpisz tekst": "Type text",
    "Media / system": "Media / system",
    "Zmiana profilu": "Profile switch",
    "Odtwórz / pauza": "Play / pause",
    "Następny utwór": "Next track",
    "Poprzedni utwór": "Previous track",
    "Głośniej": "Volume up",
    "Ciszej": "Volume down",
    "Wycisz": "Mute",
    "Blokada ekranu": "Lock screen",

    # --- kolory wiodące ---
    "Niebieski": "Blue",
    "Granatowy": "Navy",
    "Fioletowy": "Violet",
    "Różowy": "Pink",
    "Czerwony": "Red",
    "Pomarańczowy": "Orange",
    "Żółty": "Yellow",
    "Zielony": "Green",
    "Turkusowy": "Teal",
    "Grafitowy": "Graphite",

    # --- główne okno, zasobnik, pasek stanu ---
    "Przyciski": "Buttons",
    "Urządzenie": "Device",
    "Monitor": "Monitor",
    "Ustawienia": "Settings",
    "Pokaż okno": "Show window",
    "Aktywny": "Active",
    "Zakończ": "Quit",
    "aktywny": "active",
    "wstrzymany": "paused",
    "Nie znaleziono {path} - użyto ustawień domyślnych.":
        "{path} not found - using default settings.",
    "Nie udało się wczytać {path}: {error}": "Could not load {path}: {error}",
    "Plik {path} nie jest konfiguracją MAKKEY.": "{path} is not a MAKKEY configuration file.",
    "Plik {path} ma nieprawidłową zawartość: {error}": "{path} has invalid content: {error}",
    "Wczytano konfigurację z {path}": "Configuration loaded from {path}",
    "Nie udało się zarejestrować odbioru z urządzenia (Raw Input).":
        "Could not register for device input (Raw Input).",
    "Znaleziono urządzenie MAKKEY.": "MAKKEY device found.",
    "Nie znaleziono urządzenia MAKKEY - sprawdź połączenie i firmware.":
        "MAKKEY device not found - check the connection and firmware.",
    'MAKKEY wstrzymany - włącz przełącznik "Aktywny", żeby wysłać PING.':
        'MAKKEY is paused - turn on the "Active" switch to send a PING.',
    "Wysłano PING - czekam na odpowiedź.": "PING sent - waiting for a reply.",
    "Nie udało się wysłać PING (brak łącza).": "Could not send PING (no connection).",
    'Przycisk {n}: nie wysłano "{value}" - {error}':
        'Button {n}: "{value}" was not sent - {error}',
    "{action}  [wyłączony]": "{action}  [disabled]",
    "Przycisk {n}: {action}": "Button {n}: {action}",
    "Przycisk 13 (zmiana profilu)": "Button 13 (profile switch)",
    "Przycisk {n}": "Button {n}",
    '{button}: predefiniowanie włączone w profilu "{profile}"':
        '{button}: remapping enabled in profile "{profile}"',
    '{button}: predefiniowanie wyłączone w profilu "{profile}"':
        '{button}: remapping disabled in profile "{profile}"',
    "Aktywny profil: {name}": "Active profile: {name}",
    "Aktywny profil: {name} (program: {exe})": "Active profile: {name} (program: {exe})",
    "Przełączanie profili: ręczne (przycisk 13)": "Profile switching: manual (button 13)",
    "Przełączanie profili: automatyczne (po nazwie .exe)":
        "Profile switching: automatic (by .exe name)",
    "MAKKEY wstrzymany - OLED zmieniony tylko w podglądzie.":
        "MAKKEY is paused - OLED changed in the preview only.",
    'Wysłano na OLED: "{text}"': 'Sent to OLED: "{text}"',
    "Brak łącza z urządzeniem - OLED tylko w podglądzie.":
        "No connection to the device - OLED in the preview only.",
    "MAKKEY aktywny - odbiera przyciski i steruje urządzeniem":
        "MAKKEY active - receiving buttons and controlling the device",
    "MAKKEY wstrzymany - nie odbiera przycisków i nie steruje urządzeniem":
        "MAKKEY paused - not receiving buttons or controlling the device",
    "Nie udało się zapisać konfiguracji:\n{error}": "Could not save the configuration:\n{error}",
    "Zapisano konfigurację w {path}": "Configuration saved to {path}",
    "Błąd zapisu konfiguracji: {error}": "Error saving configuration: {error}",
    "Zapisano konfigurację ({name})": "Configuration saved ({name})",
    "Działa dalej w tle. Kliknij ikonę w zasobniku, żeby wrócić.":
        "Still running in the background. Click the tray icon to return.",
    "Nie udało się wyeksportować konfiguracji:\n{error}":
        "Could not export the configuration:\n{error}",
    "Wyeksportowano konfigurację do {path}": "Configuration exported to {path}",
    "Zaimportować konfigurację z pliku {name}?\n\n"
    "Bieżące ustawienia, profile, przypisania przycisków i kolory zostaną "
    "zastąpione zawartością pliku.":
        "Import the configuration from {name}?\n\n"
        "The current settings, profiles, button assignments and colors will be "
        "replaced with the contents of the file.",
    "Zaimportowano konfigurację z {path}": "Configuration imported from {path}",
    "Przywrócić ustawienia fabryczne?\n\n"
    "Wszystkie ustawienia (także język i wariant urządzenia), profile, "
    "przypisania przycisków i kolory wrócą do wartości domyślnych. "
    "Tego nie da się cofnąć - jeśli chcesz zachować obecną "
    "konfigurację, najpierw ją wyeksportuj.":
        "Restore factory settings?\n\n"
        "All settings (including the language and hardware variant), profiles, "
        "button assignments and colors will return to their defaults. "
        "This cannot be undone - if you want to keep the current "
        "configuration, export it first.",
    "Przywrócono ustawienia fabryczne.": "Factory settings restored.",

    # --- wykonywanie akcji / łącze HID ---
    "pusty skrót": "empty shortcut",
    'nieznany klawisz "{key}"': 'unknown key "{key}"',
    "system przyjął {sent} z {total} zdarzeń (błąd {code})":
        "the system accepted {sent} of {total} events (error {code})",
    "blokada ekranu nie powiodła się (błąd {code})": "locking the screen failed (error {code})",
    'nieznana akcja "{name}"': 'unknown action "{name}"',
    "przycisk {n} - wciśnięty": "button {n} - pressed",
    "pong - firmware {version}": "pong - firmware {version}",
    "błąd {code}": "error {code}",
    "ack komendy 0x{cmd:02X} - {status}": "command 0x{cmd:02X} ack - {status}",

    # --- opisy akcji ---
    "zmiana profilu": "profile switch",
    "brak akcji": "no action",
    "brak przypisanej akcji": "no action assigned",

    # --- widgety wspólne ---
    "Motyw jasny / ciemny": "Light / dark theme",
    "kliknij i naciśnij klawisze": "click and press keys",
    "kliknij i naciśnij skrót": "click and press a shortcut",
    "naciśnij  (Esc = wyczyść)": "press keys  (Esc = clear)",
    "Szybki wybór": "Quick pick",
    "WSTRZYMANY": "PAUSED",

    # --- pasek górny ---
    "Jak to działa?": "How does it work?",
    "{app} - jak to działa": "{app} - how it works",
    "Nie znaleziono urządzenia": "Device not found",
    "Urządzenie podłączone, ale MAKKEY jest wstrzymany":
        "Device connected, but MAKKEY is paused",
    "Urządzenie podłączone": "Device connected",

    # --- panel profili ---
    "Profile": "Profiles",
    "Kwadracik przy nazwie włącza i wyłącza profil":
        "The checkbox next to the name enables or disables the profile",
    "Dodaj": "Add",
    "Duplikuj": "Duplicate",
    "Usuń": "Delete",
    "Nazwa": "Name",
    "Pliki .exe (po przecinku)": ".exe files (comma-separated)",
    "np. Fusion360.exe, Fusion.exe": "e.g. Fusion360.exe, Fusion.exe",
    "Używane przy automatycznym doborze profilu.": "Used for automatic profile selection.",
    "Nieużywane w trybie ręcznym - profil wybiera przycisk 13.":
        "Not used in manual mode - button 13 selects the profile.",
    "Profil domyślny": "Default profile",
    "W trybie automatycznym działa we wszystkich programach,\n"
    "których nie wpisano w żadnym innym profilu.":
        "In automatic mode it is used in every program\n"
        "that is not listed in any other profile.",
    "W cyklu ręcznym": "In manual cycle",
    "Tryb: ręczny (przycisk 13)": "Mode: manual (button 13)",
    "Tryb: automatyczny (po nazwie .exe)": "Mode: automatic (by .exe name)",
    "Osiągnięto limit {max} profili w cyklu ręcznym.":
        "Reached the limit of {max} profiles in the manual cycle.",
    "{name}  (domyślny)": "{name}  (default)",
    "Nowy profil": "New profile",
    "{name} (kopia)": "{name} (copy)",
    "Musi zostać przynajmniej jeden profil.": "At least one profile must remain.",
    'Usunąć profil "{name}"?': 'Delete profile "{name}"?',

    # --- podgląd na żywo ---
    "Podgląd na żywo": "Live preview",
    "Brak wciśniętego przycisku": "No button pressed",
    "Czekam na sygnał z urządzenia...": "Waiting for a signal from the device...",
    "MAKKEY wstrzymany - nie odbiera przycisków": "MAKKEY paused - not receiving buttons",
    "Przycisk 13 - zmiana profilu": "Button 13 - profile switch",
    "Przełączenie na następny profil w cyklu": "Switch to the next profile in the cycle",
    "{action}  (predefiniowanie wyłączone)": "{action}  (remapping disabled)",
    "Zaznaczony: przycisk {n} - {action}": "Selected: button {n} - {action}",

    # --- zakładka Przyciski ---
    "Kliknij klawisz, żeby przypisać mu akcję i kolor. Kropka w rogu klawisza "
    "pokazuje, czy jego predefiniowanie jest włączone w tym profilu.":
        "Click a key to assign it an action and a color. The dot in the key's "
        "corner shows whether its remapping is enabled in this profile.",
    "Wiersz {row}, kolumna {col}": "Row {row}, column {col}",
    "Predefiniowanie": "Remapping",
    "Wyłączony przycisk nie wywołuje żadnej akcji, ale zachowuje\n"
    "przypisanie i kolor. Ustawienie jest osobne dla każdego profilu.":
        "A disabled button triggers no action but keeps its\n"
        "assignment and color. The setting is separate for each profile.",
    "Typ akcji": "Action type",
    "Skrót": "Shortcut",
    "Tekst": "Text",
    "Akcja": "Action",
    "Tekst do wpisania...": "Text to type...",
    "Komentarz": "Comment",
    "Do czego służy ten skrót w tym programie...":
        "What this shortcut does in this program...",
    "Twoja notatka do tego przycisku. Zapisywana osobno w każdym\n"
    "profilu, pokazywana w podglądzie i w dymku nad klawiszem.\n"
    "Nie jest wysyłana do urządzenia.":
        "Your note for this button. Saved separately in each\n"
        "profile, shown in the preview and in the key's tooltip.\n"
        "It is not sent to the device.",
    "Ręczne przełączanie": "Manual switching",
    "Profile dodaje się do cyklu w panelu po lewej (maksymalnie {max}).":
        "Profiles are added to the cycle in the panel on the left (up to {max}).",
    "Brak profili w cyklu ręcznym": "No profiles in the manual cycle",
    "Nad przyciskiem 1, obok wyświetlacza OLED": "Above button 1, next to the OLED display",
    "Przycisk nie wywołuje żadnej akcji w tym profilu.":
        "The button triggers no action in this profile.",
    "Skrót wysyłany jednorazowo przy naciśnięciu przycisku.":
        "The shortcut is sent once when the button is pressed.",
    "Podany tekst zostanie wpisany znak po znaku.":
        "The given text will be typed character by character.",
    "Sterowanie multimediami / systemem Windows.": "Media / Windows system control.",
    "Przycisk 13 przełącza profil - patrz przełącznik obok.":
        "Button 13 switches profiles - see the switch next to it.",
    "Kolor diody LED": "LED color",
    "Kolor (HEX)": "Color (HEX)",
    "Kolor zapisywany jest razem z profilem i wysyłany do urządzenia przy jego "
    "aktywacji. Zmiana jest widoczna na podglądzie od razu.":
        "The color is saved with the profile and sent to the device when the "
        "profile is activated. Changes show up in the preview immediately.",
    'Wyświetlacz OLED 0.91" ({w}x{h})': 'OLED display 0.91" ({w}x{h})',
    "Na ekranie": "On screen",
    "Wyślij na OLED": "Send to OLED",
    "Wyświetlacz pokazuje nazwę aktywnego profilu fontem 11x18 - mieści się {n} "
    "znaków, dłuższa nazwa zostanie ucięta. Standardowy font SSD1306 nie ma "
    "polskich znaków - ogonki zostaną zamienione na odpowiedniki bez znaków "
    "diakrytycznych (ą→a, ł→l).":
        "The display shows the active profile name in an 11x18 font - {n} "
        "characters fit, a longer name is cut off. The standard SSD1306 font has "
        "no Polish characters - diacritics are replaced with their plain "
        "equivalents (ą→a, ł→l).",

    # --- zakładka Urządzenie ---
    "Urządzenie {name}": "{name} device",
    "Szukanie urządzenia...": "Searching for the device...",
    "Szukaj ponownie": "Search again",
    "Test łączności (PING)": "Connection test (PING)",
    "Urządzenia HID widziane przez system": "HID devices seen by the system",
    "Nazwa produktu": "Product name",
    "VID:PID": "VID:PID",
    "Usage page / usage": "Usage page / usage",
    "Stan": "Status",
    'Przyjmowane jest wyłącznie urządzenie o nazwie "{name}" z usage page '
    "0x{page:04X} i usage 0x{usage:02X}. Reszta jest pomijana.":
        'Only a device named "{name}" with usage page 0x{page:04X} and usage '
        "0x{usage:02X} is accepted. Everything else is ignored.",
    "Protokół": "Protocol",
    'Producent "{maker}", produkt "{product}". Raport IN (ID 0x{in_id:02X}, '
    "{in_size} B) niesie bitmapę 13 przycisków; raport OUT (ID 0x{out_id:02X}, "
    "{out_size} B) - kolory diod i tekst na wyświetlacz.":
        'Manufacturer "{maker}", product "{product}". The IN report (ID 0x{in_id:02X}, '
        "{in_size} B) carries a bitmap of 13 buttons; the OUT report "
        "(ID 0x{out_id:02X}, {out_size} B) - LED colors and display text.",
    "Wersja firmware: nieznana (wyślij PING).": "Firmware version: unknown (send a PING).",
    "Wersja firmware: {version}": "Firmware version: {version}",
    "MCU: STM32G431KBT6. Przyciski podpięte indywidualnie do GPIO, diody WS2812B "
    "sterowane z tego samego układu, OLED po I2C.":
        "MCU: STM32G431KBT6. Buttons wired individually to GPIO, WS2812B LEDs "
        "driven by the same chip, OLED over I2C.",
    "podłączony": "connected",
    "nie znaleziono": "not found",
    "Podłącz urządzenie albo sprawdź, czy firmware zgłasza własny deskryptor HID "
    "(a nie klawiaturę).":
        "Connect the device or check that the firmware reports its own HID "
        "descriptor (not a keyboard).",
    "(bez nazwy)": "(no name)",
    "pomijane": "ignored",

    # --- zakładka Monitor ---
    "Wciśnięte przyciski": "Pressed buttons",
    "profil": "profile",
    "Ostatni raport": "Last report",
    "Brak odebranych danych.": "No data received.",
    "Strumień zdarzeń": "Event stream",
    "Tu pojawią się raporty z urządzenia {name} po jego podłączeniu...":
        "Reports from the {name} device will appear here once it is connected...",
    "Wyczyść": "Clear",
    "Symuluj naciśnięcie": "Simulate press",
    "Test wizualizacji bez podłączonego urządzenia":
        "Test the visualization without a connected device",
    "Pokazuj surowe raporty": "Show raw reports",
    "ID 0x{id:02X}  przycisk {n}": "ID 0x{id:02X}  button {n}",
    "przycisk {n} DÓŁ": "button {n} DOWN",

    # --- zakładka Ustawienia ---
    "Wariant urządzenia": "Hardware variant",
    "Klawiatura z podświetleniem LED (WS2812B)": "Keypad with LED backlight (WS2812B)",
    "Wyłączone: diody w urządzeniu gasną, znika wybór koloru, a podgląd\n"
    "rysuje klawisze bez poświaty. Kolory zapisane w profilach zostają nietknięte.":
        "Off: the device LEDs turn off, the color picker is hidden and the preview\n"
        "draws keys without glow. Colors saved in profiles stay untouched.",
    "Jasność diod": "LED brightness",
    'Klawiatura z wyświetlaczem OLED 0.91" ({w}x{h})': 'Keypad with 0.91" OLED display ({w}x{h})',
    "Włączone: wyświetlacz pokazuje nazwę aktywnego profilu.\n"
    'Wyłączone: ekran urządzenia jest czyszczony, znika sekcja wyświetlacza\n'
    'w zakładce "Przyciski", a podgląd rysuje urządzenie bez ekranu.':
        "On: the display shows the active profile name.\n"
        "Off: the device screen is cleared, the display section in the\n"
        '"Buttons" tab is hidden and the preview draws the device without a screen.',
    "Ustawienie opisuje sprzęt, a nie profil - obowiązuje w całym programie "
    "i zapisuje się razem z konfiguracją.":
        "This setting describes the hardware, not a profile - it applies to the "
        "whole program and is saved with the configuration.",
    "Aplikacja": "Application",
    "Język": "Language",
    "Kolor wiodący": "Accent color",
    "Uruchamiaj MAKKEY z systemem Windows": "Start MAKKEY with Windows",
    "Minimalizuj do zasobnika systemowego": "Minimize to the system tray",
    "Włączone: zamknięcie okna (X) chowa program do zasobnika i macropad\n"
    'działa dalej. Wyjście przez "Zakończ" w menu ikony w tacce.\n'
    "Wyłączone: zamknięcie okna kończy program.":
        "On: closing the window (X) hides the program in the tray and the macropad\n"
        'keeps working. Exit via "Quit" in the tray icon menu.\n'
        "Off: closing the window exits the program.",
    'Zamknięcie okna (X) chowa program do zasobnika - wyjście przez "Zakończ" '
    "w menu ikony w tacce.":
        'Closing the window (X) hides the program in the tray - exit via "Quit" '
        "in the tray icon menu.",
    "Zamknięcie okna (X) kończy program - macropad przestaje być obsługiwany.":
        "Closing the window (X) exits the program - the macropad stops being handled.",
    "Tryb przełączania profili (ręczny / automatyczny) ustawia się przełącznikiem "
    'przy akcji przycisku 13 w zakładce "Przyciski".':
        "The profile switching mode (manual / automatic) is set with the switch "
        'next to button 13\'s action in the "Buttons" tab.',
    "Skrót awaryjny": "Panic hotkey",
    "Natychmiast wyłącza przechwytywanie/remapowanie MAKKEY, np. gdy błędnie "
    'skonfigurowany skrót zacznie "zapętlać" system.':
        "Instantly turns off MAKKEY's capturing/remapping, e.g. when a misconfigured "
        'shortcut starts "looping" the system.',
    "Włączony": "Enabled",
    "Plik konfiguracyjny": "Configuration file",
    "Eksportuj...": "Export...",
    "Importuj...": "Import...",
    "Ustawienia fabryczne...": "Factory reset...",
    "Eksport zapisuje kopię całej konfiguracji (ustawienia, profile, "
    "przypisania przycisków i kolory) w wybranym pliku. Import i ustawienia "
    "fabryczne zastępują bieżącą konfigurację - jej lokalizacja (poniżej) "
    "się nie zmienia.":
        "Export saves a copy of the whole configuration (settings, profiles, "
        "button assignments and colors) to a file of your choice. Import and "
        "factory reset replace the current configuration - its location (below) "
        "stays the same.",
    "Eksportuj konfigurację": "Export configuration",
    "Importuj konfigurację": "Import configuration",
    "Zmień lokalizację...": "Change location...",
    "Wróć do domyślnej": "Restore default",
    "Otwórz folder": "Open folder",
    "Zmiana lokalizacji zapisuje bieżącą konfigurację w nowym miejscu i od tej "
    "pory MAKKEY będzie z niego korzystał.":
        "Changing the location saves the current configuration in the new place "
        "and MAKKEY will use it from then on.",
    "Wybierz plik konfiguracyjny": "Choose configuration file",
    "Plik JSON (*.json)": "JSON file (*.json)",
    "Nie udało się otworzyć folderu:\n{error}": "Could not open the folder:\n{error}",

    # --- aktualizacje (tylko pasek stanu) ---
    "Sprawdzanie aktualizacji...": "Checking for updates...",
    "Masz najnowszą wersję ({version}).": "You have the latest version ({version}).",
    "Dostępna aktualizacja: {latest} (masz {current}).":
        "Update available: {latest} (you have {current}).",
    "Nie udało się sprawdzić aktualizacji: {error}": "Could not check for updates: {error}",
    "Aktualizowanie...": "Updating...",
    "Pobieranie: {done:.1f} / {total:.1f} MB": "Downloading: {done:.1f} / {total:.1f} MB",
    "Pobieranie: {done:.1f} MB": "Downloading: {done:.1f} MB",
    "Aktualizacja zainstalowana - zadziała po ponownym uruchomieniu programu.":
        "Update installed - it takes effect after restarting the program.",
    "Aktualizacja nie powiodła się: {error}": "Update failed: {error}",
    "Nie udało się uruchomić programu ponownie: {error}": "Could not restart the program: {error}",
    "git nie odpowiedział w ciągu {n} s": "git did not respond within {n} s",
    "nie udało się uruchomić gita: {error}": "could not run git: {error}",
    "bieżąca gałąź nie śledzi gałęzi w repozytorium (git branch -u origin/{branch})":
        "the current branch does not track a repository branch "
        "(git branch -u origin/{branch})",
    "{n} nowych zmian": "{n} new changes",
    "w repozytorium nie ma jeszcze żadnego wydania (Releases)":
        "the repository has no releases yet",
    "repozytorium jest prywatne, a git na tym komputerze nie jest zalogowany do GitHuba":
        "the repository is private and git on this computer is not signed in to GitHub",
    "wydanie {tag} nie ma dołączonego pliku {name}": "release {tag} has no {name} attached",
    "pobrany plik nie jest programem exe": "the downloaded file is not an exe program",
    "nie można podmienić pliku {name}: {error}": "cannot replace {name}: {error}",
    "GitHub zwrócił błąd {code}": "GitHub returned error {code}",
    "brak połączenia z GitHubem ({error})": "no connection to GitHub ({error})",
}
