# MAKKEY 1.1.2

Aplikacja na Windows do konfiguracji macropada MAKKEY (13 przycisków,
diody WS2812B, wyświetlacz OLED 0.91", MCU STM32G431KBT6).

Stan: interfejs działa, konfiguracja zapisuje się do JSON, odbiór raportów
z urządzenia, wysyłka komend (kolory, OLED), wykonywanie akcji przycisków
(skrót, tekst, media) oraz przełączanie profili - ręczne przyciskiem 13
i automatyczne po nazwie .exe - są zaimplementowane.
Do zrobienia: autostart.

## Uruchomienie

```
pip install -r requirements.txt
python main.py
```

## Budowanie pliku exe

Dwuklik w **`build_exe.bat`** (albo `python build_exe.py`). Skrypt sam
doinstaluje brakujące pakiety, narysuje ikonę i zawoła PyInstallera; efekt
to `dist\MAKKEY.exe` - jeden plik, bez okna konsoli, działający bez Pythona
na docelowej maszynie. Pliki robocze lądują w `build\`.

## Struktura

```
main.py                     punkt wejścia
build_exe.bat / .py         budowanie dist\MAKKEY.exe
aktualizuj_repo.bat / .py   commit + wysłanie zmian na GitHub
app/
  constants.py              geometria, protokół HID, OLED, limity
  models.py                 profile + mapowania przycisków (w pamięci)
  config.py                 zapis/odczyt config.json + zmiana lokalizacji
  theme.py                  motyw jasny/ciemny, kolor wiodący, ikona (QSS)
  main_window.py            spięcie paneli i sygnałów
  i18n.py                   tr() + wybór języka interfejsu
  lang_en.py                tłumaczenie angielskie (polski oryginał -> EN)
  key_sender.py             wysyłanie skrótów / tekstu / mediów (SendInput)
  app_watcher.py            program na pierwszym planie (auto-dobór profilu)
  updater.py                aktualizacje z repozytorium (git / GitHub Releases)
  device/
    hid_link.py             odbiór raportów IN + wysyłka raportów OUT
  widgets/
    common.py               karty, kropka stanu, przełącznik motywu, HotkeyEdit
    macropad.py             rysowany, interaktywny widok urządzenia
    top_bar.py              logo, stan, info, motyw, przełącznik Aktywny
    profile_panel.py        lista profili + ustawienia profilu
    device_preview.py       podgląd na żywo + info o wciśniętym przycisku
    tab_keys.py             macropad + edytor przycisku (akcja, kolor, OLED)
    tab_device.py           wykrywanie urządzenia wśród urządzeń HID
    tab_monitor.py          podgląd zdarzeń z urządzenia
    tab_settings.py         wariant sprzętu, wygląd, skrót awaryjny, config
                            (eksport / import / fabryczne, lokalizacja)
    toggle_switch.py        przełącznik rysowany ręcznie
    color_picker.py         własny wybór koloru diody LED
```

Wygląd (paleta, karty, kolor wiodący, przełącznik motywu, pola
przechwytujące skrót) jest wspólny z MAKMOUSE - obie aplikacje tego samego
autora mają sprawiać wrażenie jednego programu.

## Repozytorium i aktualizacje

Kod leży w prywatnym repozytorium https://github.com/makao1253/MAKKEY
(gałąź `main`). Do repozytorium nie trafiają `build/`, `dist/`, ikona
generowana przez `build_exe.py` ani `config.json` - każdy komputer ma
własną konfigurację (patrz `.gitignore`).

**Wysłanie zmian** - dwuklik w `aktualizuj_repo.bat` (albo
`python aktualizuj_repo.py "opis zmian"`). Skrypt pokazuje zmienione pliki,
pyta o opis, robi commit i push. Zmiany z innego komputera najpierw
dociąga (`pull --rebase`), więc push nie zostanie odrzucony.

**Aktualizacja programu** - logika jest w `app/updater.py`, ale program
**nie ma teraz widoku aktualizacji** (sekcji w Ustawieniach, dymków, okien)
i sam ich nie sprawdza. Metody w `MainWindow` są gotowe do podpięcia pod
nowy widok: `_check_updates()` -> `_install_update()` -> `_restart_app()`,
a stan wypisują w pasku stanu. Sposób aktualizacji zależy od tego, jak
program jest uruchomiony:

| Uruchomienie | Skąd nowa wersja | Jak |
|---|---|---|
| `python main.py` w klonie repozytorium | nowe commity w `origin/main` | `git pull --ff-only`, potem restart |
| `MAKKEY.exe` | najnowsze wydanie (Releases) z plikiem `MAKKEY.exe` | pobranie, podmiana pliku exe, restart |

Lokalne zmiany kolidujące z przychodzącymi zatrzymują `git pull` (nic nie
jest scalane po cichu). Repozytorium jest prywatne, więc program pyta
GitHuba tokenem zapisanym przez gita (`git credential fill`) - na komputerze
z exe musi być zainstalowany git zalogowany do GitHuba (wystarczy raz
zrobić `git clone` albo `git push`).

**Wydanie nowej wersji exe:**

1. podnieś `APP_VERSION` w `app/constants.py` (np. `1.2.0`),
2. `build_exe.bat`,
3. `aktualizuj_repo.bat`,
4. na GitHubie: Releases -> *Draft a new release* -> tag `v1.2.0` ->
   dołącz `dist\MAKKEY.exe` (nazwa pliku musi zostać `MAKKEY.exe`) ->
   *Publish release*.

Program porównuje numer z tagu wydania ze swoim `APP_VERSION` - wydanie
bez podniesionego numeru nie zostanie uznane za aktualizację.

## Język interfejsu

Polski lub angielski - wybór w Ustawieniach -> Aplikacja -> Język. Zmiana
działa od razu: okno zapisuje stan i buduje się od nowa w tym samym procesie.

Teksty przechodzą przez `tr("polski oryginał", pole=...)` z `app/i18n.py`,
a tłumaczenia leżą w `app/lang_en.py` (klucz = polski tekst). Typy akcji
i akcje multimedialne zapisują się w `config.json` zawsze
po polsku i są tłumaczone dopiero przy wyświetlaniu - konfiguracja działa
tak samo w obu językach. Nowy tekst w interfejsie = `tr(...)` w kodzie
i wpis w `lang_en.py`; brak wpisu oznacza po prostu polski tekst.

## Konfiguracja

Domyślna lokalizacja: `%APPDATA%\MAKKEY\config.json`. Ścieżkę można zmienić
w Ustawieniach - nowa lokalizacja zapamiętywana jest we wskaźniku
`%APPDATA%\MAKKEY\location.json`, a bieżąca konfiguracja jest od razu
zapisywana w nowym miejscu. Zapis jest opóźniony o ~0,7 s od ostatniej
zmiany, żeby nie pisać na dysk przy każdym wciśniętym znaku.

Nad ścieżką, w tej samej karcie Ustawień, są trzy przyciski:

* **Eksportuj...** - kopia całej konfiguracji (ustawienia, profile,
  przypisania, kolory) w wybranym pliku; domyślnie
  `Dokumenty\MAKKEY-config-RRRR-MM-DD.json`. Plik ma ten sam format co
  `config.json` (plus pole `app_version` z wersją programu, który go zapisał),
  więc oba są wymienne.
* **Importuj...** - wczytuje taki plik. Najpierw jest w całości sprawdzany
  (zły JSON albo plik bez sekcji `settings` / `profiles` = komunikat, nic się
  nie zmienia), potem program pyta o potwierdzenie.
* **Ustawienia fabryczne...** - po potwierdzeniu wszystko wraca do wartości
  domyślnych: ustawienia (także język i wariant urządzenia), profile
  przykładowe, przypisania i kolory.

Import i ustawienia fabryczne nadpisują bieżący plik konfiguracyjny - jego
lokalizacja się nie zmienia - a okno buduje się od nowa, tak jak po zmianie
języka. Cofnąć się tego nie da, więc przed nimi warto zrobić eksport.

Pliki z wersji 1 wczytują się bez zmian: motyw z pola `dark_theme` jest
przepisywany na `theme`, a nieznane wtedy pola (predefiniowanie przycisku,
wariant sprzętowy) dostają wartości domyślne.

## Odbiór i wysyłka - surowy HID

Urządzenie ma **własny deskryptor raportu** (vendor-defined usage page
`0xFF00`, usage `0x01`) i **nie jest klawiaturą**, więc:

| Kierunek | Sposób | Dlaczego tak |
|---|---|---|
| urządzenie → host | Raw Input (`WM_INPUT`) na usage page `0xFF00` | dostajemy komplet bajtów raportu razem z uchwytem urządzenia źródłowego, bez otwierania go na odczyt, także gdy okno nie ma fokusu |
| host → urządzenie | `CreateFileW` + `WriteFile` (zapas: `HidD_SetOutputReport`) | urządzenie nie jest klawiaturą, więc system nie trzyma go na wyłączność |

Wszystko siedzi w `app/device/hid_link.py` na czystym `ctypes` - bez
dodatkowych zależności (hidapi nie jest potrzebne).

### Wykrywanie urządzenia

Przyjmowane jest **wyłącznie** urządzenie, które ma jednocześnie:

* usage page `0xFF00` i usage `0x01`,
* nazwę produktu zawierającą `MAKKEY` (`iProduct` z deskryptora USB).

Gdy nazwy nie da się odczytać, zapasowo sprawdzane jest VID/PID
(`0483:572B`). Reszta urządzeń HID jest pomijana - zakładka "Urządzenie"
pokazuje pełną listę razem ze stanem, więc widać, dlaczego coś nie zostało
przyjęte.

### Protokół

Raport IN (`ID 0x01`, 1 + 8 bajtów) - urządzenie → host:

| Bajt | Znaczenie |
|---|---|
| 0 | typ: `0x01` stan przycisków, `0x02` pong/wersja, `0x03` ACK |
| 1 | bitmapa przycisków 1-8 |
| 2 | bitmapa przycisków 9-13 |
| 3 | licznik sekwencyjny |
| 4 | flagi firmware (bit 0 debug UART, bit 1 OLED wykryty) |

Raport OUT (`ID 0x02`, 1 + 63 bajty) - host → urządzenie:

| Kod | Nazwa | Parametry |
|---|---|---|
| `0x10` | SET_LED_ONE | `[nr przycisku 1-13, R, G, B]` |
| `0x11` | SET_LED_ALL | `13 x (R, G, B)` dla przycisków 1-13 |
| `0x12` | SAVE_TO_FLASH | - |
| `0x13` | SET_BRIGHTNESS | `[0-255]` |
| `0x20` | OLED_TEXT | `[linia 0, długość, ASCII...]` |
| `0x21` | OLED_CLEAR | - |
| `0x30` | PING | - (odpowiedź: raport IN typu `0x02`) |

Diody adresowane są numerem przycisku - na kolejność w łańcuchu na płytce
(13, 1-4, 8-5, 9-12) przelicza je firmware.

Pełna specyfikacja firmware: `firmware/PROMPT.md`.

## Układ urządzenia

```
[13] [ ---- OLED 0.91" ---- ]
[ 1] [ 2] [ 3] [ 4]
[ 5] [ 6] [ 7] [ 8]
[ 9] [10] [11] [12]
```

Przycisk 13 służy wyłącznie do zmiany profilu (akcja zablokowana na
"Zmiana profilu"). Przełącznik obok tej akcji wybiera tryb:

* **ręczny** - przycisk 13 przechodzi cyklicznie po profilach oznaczonych
  jako "W cyklu ręcznym", maksymalnie 4 (`MAX_MANUAL_PROFILES`),
* **automatyczny** - profil dobierany po nazwie procesu aktywnego okna
  (pole "Pliki .exe" w panelu profili).

W trybie automatycznym zmianę okna zgłasza system (hak
`EVENT_SYSTEM_FOREGROUND`, `app/app_watcher.py`), więc profil przełącza się
od razu. Wybierany jest pierwszy **włączony** profil, który ma dany program
na liście; nazwy można wpisywać z `.exe` lub bez, wielkość liter nie ma
znaczenia. Program spoza wszystkich list dostaje **profil domyślny**.
Okna samego MAKKEY są pomijane - klikanie w konfigurator nie zmienia profilu,
a po powrocie do programu jego profil wraca na miejsce.

## Zasobnik systemowy

Program zostaje w zasobniku, bo po zamknięciu okna nikt inny nie odbiera
raportów z macropada. Zamknięcie okna (X) **chowa** go do tacki, a menu pod
prawym przyciskiem ikony daje "Pokaż okno", przełącznik "Aktywny"
i "Zakończ". Kliknięcie ikony przywraca okno.

Zachowanie steruje opcja "Minimalizuj do zasobnika systemowego"
w Ustawieniach - wyłączona sprawia, że zamknięcie okna kończy program.
Gdy system nie udostępnia zasobnika, program też zwyczajnie się zamyka.

W Windows 11 nowa ikona trafia domyślnie do schowka pod strzałką `^`
w pasku zadań; można ją stamtąd przeciągnąć na stałe.

## Predefiniowanie przycisków

Każdy przycisk ma w każdym profilu **osobny włącznik** ("Predefiniowanie"
w zakładce Przyciski). Wyłączony przycisk nie wywołuje żadnej akcji, ale
zachowuje przypisanie i kolor - po ponownym włączeniu wszystko wraca bez
przepisywania ustawień. Stan widać na podglądzie na żywo jako kropkę
w lewym górnym rogu klawisza: **zielona** = działa, **czerwona** = wyłączony.

Cały profil włącza się i wyłącza kwadracikiem przy jego nazwie na liście.

## Komentarze do przycisków

Pole "Komentarz" w zakładce Przyciski to własna notatka: do czego dany
skrót służy w programie profilu (np. `Ctrl+E` - "Wyciągnięcie" w Fusion 360).
Komentarz jest osobny dla każdego przycisku w każdym profilu, zapisuje się
w `config.json` (pole `comment` przycisku) i jest widoczny w dymku po
najechaniu na klawisz podglądu, pod opisem zaznaczonego / wciśniętego
przycisku i w strumieniu zdarzeń Monitora. Nie wpływa na akcję i nie trafia
do urządzenia.

## Wykonywanie akcji

Po wciśnięciu przycisku na urządzeniu MAKKEY wykonuje jego akcję przez
WinAPI `SendInput` (`app/key_sender.py`) - zdarzenia trafiają do okna na
pierwszym planie tak samo, jak z prawdziwej klawiatury:

* **Skrót klawiszowy** - modyfikatory w dół, klawisz, puszczenie w odwrotnej
  kolejności; jednorazowo przy naciśnięciu,
* **Wpisz tekst** - znaki Unicode, niezależnie od układu klawiatury,
* **Media / system** - klawisze multimedialne, blokada ekranu.

Symulacja z zakładki Monitor tylko podświetla podgląd - skrót trafiłby do
okna MAKKEY. Nieudana wysyłka ląduje w pasku stanu i w strumieniu zdarzeń.

Program uruchomiony jako administrator przyjmuje wstrzyknięte klawisze
wyłącznie od programów, które też działają jako administrator (UIPI) -
Windows nie zgłasza wtedy błędu, skrót po prostu nie dociera.

## Wariant sprzętowy

W Ustawieniach wybiera się, czy klawiatura ma podświetlenie LED i czy ma
wyświetlacz. Zaznaczona opcja oznacza, że urządzenie dostaje kolory diod
i nazwę profilu. Wyłączenie którejkolwiek opcji **gasi** ten sprzęt
w urządzeniu (diody czarne / ekran wyczyszczony), **chowa** powiązane sekcje
w całym programie (wybór koloru, sekcja OLED) i przestawia podgląd: bez
diod klawisze rysowane są bez poświaty, bez wyświetlacza - bez ekranu.
Ponowne zaznaczenie od razu wysyła bieżący profil. Kolory zapisane
w profilach zostają nietknięte.

### OLED 0.91"

Wyświetlacz to SSD1306 128x32 px na I2C i pokazuje **zawsze nazwę aktywnego
profilu** - zmienia się razem z profilem (ręcznie, przyciskiem 13 albo
automatycznie po programie) i od razu po zmianie nazwy. Firmware rysuje ją
fontem 11x18, wyśrodkowaną: mieści się jedna linia po 11 znaków, dłuższa
nazwa jest ucinana. Standardowy font nie ma polskich znaków, więc ogonki są
transliterowane (ą→a, ł→l) po stronie aplikacji - dokładnie tak samo, jak
robi to firmware, żeby podgląd pokazywał to, co naprawdę pojawi się na
ekranie. Przycisk "Wyślij na OLED" w zakładce Przyciski wysyła nazwę
ponownie.
