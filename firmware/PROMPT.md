# Prompt: firmware STM32G431KBT6 dla macropada MAKKEY

> Skopiuj całość poniżej jako zadanie dla narzędzia piszącego kod firmware.

---

## Zadanie

Napisz kompletny firmware w C dla mikrokontrolera **STM32G431KBT6** (LQFP32),
obsługujący macropad **MAKKEY**: 13 przycisków, 13 diod adresowalnych
WS2812B, wyświetlacz OLED 0.91" (SSD1306, I2C) oraz komunikację z aplikacją
na PC przez **USB HID z własnym (vendor-defined) deskryptorem raportu**.

Urządzenie **nie może** zgłaszać się jako klawiatura. Ma być generycznym
urządzeniem HID przesyłającym surowe dane, bo całe remapowanie robi
aplikacja MAKKEY po stronie PC.

Użyj STM32 HAL + CubeMX (lub równoważnej konfiguracji zegarów i peryferiów
zapisanej wprost w kodzie). Kod ma się kompilować bez ostrzeżeń.

---

## 1. Kontekst: dlaczego surowy deskryptor

Obecnie urządzenie jest zwykłą klawiaturą HID (nazwa `MAKKey`, `0483:572B`)
i wysyła litery a-l. To rozwiązanie zostaje **porzucone**, bo:

* Windows zna tylko `VK_F13`..`VK_F24` (12 klawiszy), a z tego F13-F18 są
  już zajęte przez inną aplikację tego samego autora (MAKMOUSE) - zostaje
  6 klawiszy przy 13 potrzebnych;
* dopóki urządzenie jest klawiaturą, wciśnięte litery trafiają też do
  aktywnego okna i nie da się ich zablokować bez sterownika;
* Windows otwiera klawiatury na wyłączność, więc host nie może czytać
  z urządzenia przez hidapi.

Po przejściu na własny deskryptor wszystkie trzy problemy znikają naraz.

---

## 2. Sprzęt i wyprowadzenia

| Pin | Funkcja | Uwagi |
|---|---|---|
| PF0 | BTN12 | pin OSC_IN - patrz sekcja o zegarach |
| PF1 | BTN5 | pin OSC_OUT - patrz sekcja o zegarach |
| PA0 | BTN3 | |
| PA1 | BTN6 | |
| PA2 | BTN10 **lub** USART2_TX | **konflikt - patrz sekcja 4** |
| PA3 | BTN7 **lub** USART2_RX | **konflikt - patrz sekcja 4** |
| PA4 | BTN2 | |
| PA5 | BTN9 | |
| PA6 | BTN8 | |
| PA7 | BTN1 | |
| PB5 | BTN13 | przycisk zmiany profilu |
| PB6 | BTN4 | |
| PA10 | BTN11 | 
| PA8 | I2C_SDA (OLED) | |
| PA9 | I2C_SCL (OLED) | |
| PB0 | WS2812B DIN | 13 diod w łańcuchu |
| PA11 | USB_DM | |
| PA12 | USB_DP | |
| PA13 | SWDIO | nie przekonfigurowywać |
| PA14 | SWCLK | nie przekonfigurowywać |

Założenie o przyciskach: każdy przycisk zwiera pin do **GND**, więc
włącz wewnętrzne podciągnięcie (`GPIO_PULLUP`), a stan wciśnięty to
**poziom niski**. Jeśli w rzeczywistości są podciągnięte do VCC, zmiana
ma być możliwa jedną stałą `BUTTON_ACTIVE_LOW`.

---

## 3. DO ROZSTRZYGNIĘCIA: 

Wolne piny w obudowie LQFP32 po uwzględnieniu wszystkiego powyżej:
`PA10`, `PA15`, `PB3`, `PB4`, `PB7` (oraz `PB1`, jeśli występuje
w danym wariancie - sprawdź w datasheet).

**Domyślnie przyjmij `PA10` dla BTN11** i wydziel to jedną, dobrze
widoczną stałą w `board_config.h`, żeby zmiana na inny pin była
jednolinijkowa:

```c
#define BTN11_PORT   GPIOA
#define BTN11_PIN    GPIO_PIN_10   /* TODO: potwierdzić z projektem PCB */
```

`PB3` i `PB4` to domyślnie JTDO / NJTRST - działają jako GPIO przy
samym SWD, ale jeśli to możliwe, wybierz `PA10` lub `PB7`.

---

## 4. DO ROZSTRZYGNIĘCIA: konflikt UART z BTN10 i BTN7

`PA2` i `PA3` są jednocześnie przypisane do przycisków (BTN10, BTN7)
i do UART-u diagnostycznego (USART2_TX / USART2_RX). Nie da się mieć
obu naraz.

Zaimplementuj to jako **jedną flagę o trzech stanach**, żeby dało się
przełączać jedną linijką:

```c
/* 0 = UART wyłączony, PA2/PA3 to zwykłe przyciski (wersja finalna)
 * 1 = tylko TX na PA2  -> BTN10 nieaktywny, BTN7 DZIAŁA  (zalecane do debugu)
 * 2 = TX+RX na PA2/PA3 -> BTN10 i BTN7 nieaktywne
 */
#define DEBUG_UART_MODE  1
```

**Tryb 1 jest zalecany**: do wypisywania diagnostyki nie potrzeba
odbioru, więc wystarczy poświęcić jeden przycisk zamiast dwóch.

Zachowanie w trybach 1 i 2:

* piny zajęte przez UART nie są inicjalizowane jako wejścia przycisków;
* bity odpowiadających im przycisków w raporcie USB są **zawsze 0**;
* przy starcie firmware wypisuje ostrzeżenie, np.
  `[WARN] DEBUG_UART_MODE=1 -> BTN10 (PA2) nieaktywny`.

Parametry UART: **115200 8N1**, bez sterowania przepływem.

---

## 5. Zegary - uwaga krytyczna

`PF0` i `PF1` to `OSC_IN` / `OSC_OUT`. Skoro są zajęte przez przyciski,
**nie ma zewnętrznego rezonatora** i konfiguracja musi być bezkwarcowa:

* `SYSCLK` z PLL zasilanego z **HSI16** (docelowo 170 MHz);
* zegar USB z **HSI48**, zestrojony przez **CRS** synchronizowany
  z ramkami SOF magistrali USB (`RCC_CRS_SYNC_SOURCE_USB`).

Bez włączonego CRS enumeracja USB będzie działać niestabilnie lub wcale.
Nie konfiguruj HSE.

---

## 6. Deskryptor raportu HID

Jedna kolekcja aplikacyjna z **vendor-defined usage page `0xFF00`**.
Jeden raport wejściowy (urządzenie -> host) i jeden wyjściowy
(host -> urządzenie). Rozróżnianie komend odbywa się **bajtem komendy
wewnątrz raportu**, a nie osobnymi Report ID - dzięki temu po stronie
hosta jest jeden stały rozmiar bufora, co znacznie upraszcza kod hidapi.

```c
static const uint8_t MAKKEY_ReportDescriptor[38] = {
    0x06, 0x00, 0xFF,        /* Usage Page (Vendor Defined 0xFF00)      */
    0x09, 0x01,              /* Usage (0x01) - MAKKEY                   */
    0xA1, 0x01,              /* Collection (Application)                */

    /* --- IN: stan przycisków / odpowiedzi (device -> host) --------- */
    0x85, 0x01,              /*   Report ID (1)                         */
    0x09, 0x02,              /*   Usage (0x02)                          */
    0x15, 0x00,              /*   Logical Minimum (0)                   */
    0x26, 0xFF, 0x00,        /*   Logical Maximum (255)                 */
    0x75, 0x08,              /*   Report Size (8 bitów)                 */
    0x95, 0x08,              /*   Report Count (8 bajtów)               */
    0x81, 0x02,              /*   Input (Data, Var, Abs)                */

    /* --- OUT: komendy (host -> device) ----------------------------- */
    0x85, 0x02,              /*   Report ID (2)                         */
    0x09, 0x03,              /*   Usage (0x03)                          */
    0x15, 0x00,              /*   Logical Minimum (0)                   */
    0x26, 0xFF, 0x00,        /*   Logical Maximum (255)                 */
    0x75, 0x08,              /*   Report Size (8 bitów)                 */
    0x95, 0x3F,              /*   Report Count (63 bajty)               */
    0x91, 0x02,              /*   Output (Data, Var, Abs)               */

    0xC0                     /* End Collection                          */
};
```

Rozmiary na magistrali: raport IN = 1 (ID) + 8 = **9 bajtów**,
raport OUT = 1 (ID) + 63 = **64 bajty**.

### Deskryptory USB

| Pole | Wartość | Uzasadnienie |
|---|---|---|
| `bDeviceClass` | `0x00` | klasa deklarowana na poziomie interfejsu |
| `bInterfaceClass` | `0x03` | HID |
| `bInterfaceSubClass` | `0x00` | **nie boot** - inaczej system uzna to za klawiaturę |
| `bInterfaceProtocol` | `0x00` | **żaden** - jw. |
| `bcdHID` | `0x0111` | |
| `bNumEndpoints` | `2` | |
| EP IN | `0x81`, Interrupt, 64 B, `bInterval = 1` | 1 ms |
| EP OUT | `0x01`, Interrupt, 64 B, `bInterval = 1` | 1 ms |
| `bMaxPower` | `250` (= 500 mA) | patrz budżet prądowy |
| Manufacturer | `"MAK"` | |
| Product | `"MAKKEY"` | aplikacja szuka urządzenia po tym ciągu |
| Serial | unikalny, np. z UID96 mikrokontrolera | |

`bInterfaceSubClass = 0` i `bInterfaceProtocol = 0` są **kluczowe**:
przy wartościach boot-keyboard Windows przejąłby urządzenie na wyłączność
i hidapi nie mogłoby go otworzyć.

**VID/PID**: obecne `0483:572B` używa VID-a należącego do
STMicroelectronics. Do prototypu przejdzie, ale do czegokolwiek
rozpowszechnianego weź własny identyfikator - np. darmowy PID
z puli `pid.codes` (VID `0x1209`). Wartości mają siedzieć w jednym
nagłówku, żeby dało się je podmienić bez szukania po kodzie.

---

## 7. Protokół

### Raport IN (Report ID `0x01`, 8 bajtów payloadu)

| Bajt | Znaczenie |
|---|---|
| 0 | typ zdarzenia: `0x01` = stan przycisków, `0x02` = pong/wersja, `0x03` = ACK komendy |
| 1 | bitmapa przycisków 1-8 (bit 0 = BTN1, ... bit 7 = BTN8) |
| 2 | bitmapa przycisków 9-13 (bit 0 = BTN9, ... bit 4 = BTN13; bity 5-7 = 0) |
| 3 | licznik sekwencyjny, inkrementowany co raport (wykrywanie zgubionych) |
| 4 | flagi firmware: bit 0 = debug UART aktywny, bit 1 = OLED wykryty |
| 5-7 | zarezerwowane, zera |

Dla `0x02` (pong): bajt 1 = wersja major, 2 = minor, 3 = patch.
Dla `0x03` (ACK): bajt 1 = echo kodu komendy, 2 = status (`0` = OK).

Raport wysyłaj **przy każdej zmianie stanu** któregokolwiek przycisku.
Dodatkowo wysyłaj raport podtrzymujący co 500 ms, żeby host mógł wykryć
zerwanie łączności.

### Raport OUT (Report ID `0x02`, 63 bajty payloadu)

Bajt 0 = kod komendy, dalej parametry:

| Kod | Nazwa | Parametry |
|---|---|---|
| `0x10` | SET_LED_ONE | `[1]` = numer diody 1-13, `[2..4]` = R, G, B |
| `0x11` | SET_LED_ALL | `[1..39]` = 13 x (R, G, B), kolejno dla diod 1-13 |
| `0x12` | SAVE_TO_FLASH | brak - zapisuje bieżące kolory do pamięci nieulotnej |
| `0x13` | SET_BRIGHTNESS | `[1]` = jasność globalna 0-255 |
| `0x20` | OLED_TEXT | `[1]` = numer linii (0/1), `[2]` = długość, `[3..]` = ASCII |
| `0x21` | OLED_CLEAR | brak |
| `0x30` | PING | brak - urządzenie odpowiada raportem IN typu `0x02` |

Nieznane kody komend należy **zignorować** i odesłać ACK ze statusem
błędu, nigdy nie zawieszać urządzenia.

Kolory z hosta przychodzą w kolejności **R, G, B**. WS2812B oczekuje
**G, R, B** - przestawienie jest zadaniem firmware'u.

---

## 8. Obsługa przycisków

* próbkowanie co **1 ms** (przerwanie timera albo SysTick);
* **debounce 8 ms**: zmiana stanu akceptowana dopiero po ośmiu kolejnych
  jednakowych odczytach;
* pełny N-key rollover - wszystkie 13 przycisków niezależnie, bez limitu
  jednoczesnych wciśnięć (to jedna z głównych przewag nad trybem klawiatury);
* obsługa przycisków musi działać także wtedy, gdy USB nie jest
  podłączone (diody i OLED mają reagować dalej).

---

## 9. Diody WS2812B na PB0

Sterowanie **PWM + DMA** (bez bit-bangingu i bez blokowania CPU).

* `PB0` = `TIM3_CH3` (AF2) - potwierdź numer AF w datasheet;
* przy `TIMxCLK = 170 MHz` i okresie 1,25 µs: `PSC = 0`, `ARR = 211`
  (212 taktów = 1,247 µs, błąd 0,24 % - mieści się w tolerancji);
* `T0H` = 0,4 µs -> `CCR = 68`;
* `T1H` = 0,8 µs -> `CCR = 136`;
* reset: minimum 50 µs stanu niskiego -> dopisz co najmniej 48 zerowych
  słów na końcu bufora DMA;
* bufor: 13 diod x 24 bity = 312 słów + 48 słów resetu = **360 x uint16_t**;
* kolejność bitów: MSB pierwszy, kolejność bajtów **G, R, B**.

### Budżet prądowy - ważne

13 diod x ~60 mA (pełna biel) = **780 mA**, a USB daje maksymalnie
500 mA. Zaimplementuj **twarde ograniczenie jasności**:

* stała `LED_MAX_TOTAL_CURRENT_MA` (domyślnie **350 mA**);
* przed wysłaniem ramki policz szacowany pobór
  (suma wszystkich składowych RGB x ~20 mA / 255) i jeśli przekracza
  limit, przeskaluj wszystkie kolory proporcjonalnie;
* domyślna jasność globalna po starcie: **64/255**.

### Poziom logiczny - uwaga sprzętowa

WS2812B zasilane 5 V wymaga `VIH >= 0,7 x VDD = 3,5 V`, a STM32 wystawia
3,3 V. Bywa, że działa, ale jest to poza specyfikacją. Jeśli pojawią się
losowe błędne kolory, przyczyna jest najpewniej tutaj - rozwiązania to
konwerter poziomów na linii danych, zasilenie diod przez diodę
krzemową (~4,4 V, co obniża próg) albo użycie SK6812. W kodzie zostaw
o tym komentarz przy inicjalizacji.

Dodatkowo (sprzęt, nie firmware): kondensator ~1000 µF na zasilaniu diod
i rezystor 330-470 Ω szeregowo na linii danych.

---

## 10. Wyświetlacz OLED

SSD1306 128x32, I2C na PA8 (SDA) / PA9 (SCL), adres 7-bitowy `0x3C`.
Prawdopodobnie `I2C2` - **zweryfikuj numer peryferium i AF w datasheet**
dla STM32G431 (CubeMX rozwiąże to automatycznie). Jeśli sprzętowe I2C
nie wypada na tych pinach, dopuszczalne jest programowe I2C.

Bibliotekę graficzną dostarczy autor projektu później, więc na teraz:

* zainicjalizuj I2C i wykryj obecność wyświetlacza (`HAL_I2C_IsDeviceReady`);
* wystaw prosty interfejs, który później podepnie się pod bibliotekę:

```c
void oled_init(void);
bool oled_present(void);
void oled_clear(void);
void oled_write_line(uint8_t line, const char *text);
```

* na razie `oled_write_line` może tylko logować tekst na UART -
  implementacja rysowania dojdzie później;
* przy odbiorze komendy `0x20` **przefiltruj polskie znaki** na
  odpowiedniki ASCII (ą->a, ć->c, ę->e, ł->l, ń->n, ó->o, ś->s,
  ź/ż->z oraz wielkie litery), bo standardowy font SSD1306 ich nie ma.

---

## 11. Diagnostyka na UART

Gdy `DEBUG_UART_MODE != 0`, wypisuj czytelne, jednolinijkowe komunikaty:

```
[BOOT] MAKKEY fw 0.1.0  DEBUG_UART_MODE=1
[WARN] BTN10 (PA2) nieaktywny - pin zajety przez UART
[CLK ] SYSCLK=170MHz  USB=HSI48+CRS  OK
[USB ] enumeracja OK, adres=7
[BTN ] wcisniety  #5   bitmapa=0010 0000 0000 0  seq=41
[BTN ] puszczony  #5   bitmapa=0000 0000 0000 0  seq=42
[RX  ] cmd=0x10 SET_LED_ONE  led=3 RGB=(255,0,64)
[RX  ] cmd=0x11 SET_LED_ALL  13 diod, suma pradu ~210mA
[LED ] ramka wyslana, jasnosc=64, ograniczenie=nie
[RX  ] cmd=0x20 OLED_TEXT  linia=0 "FUSION 360"
[ERR ] cmd=0x99 nieznana komenda - zignorowano
```

Wymagania:

* logowanie **nie może blokować** pętli głównej ani przerwań - użyj
  UART przez DMA albo bufora kołowego opróżnianego w tle;
* przy `DEBUG_UART_MODE = 0` cały kod logowania ma zniknąć
  z wynikowego binarium (makro puste, nie pusta funkcja);
* logi mają pozwolić zweryfikować **wszystkie trzy ścieżki naraz**:
  poprawność odczytu przycisków, poprawność wysyłki raportów USB
  do systemu oraz poprawność kolorów przychodzących z aplikacji MAKKEY.

---

## 12. Struktura projektu

```
Core/Inc, Core/Src            kod generowany przez CubeMX
USB_Device/                   warstwa USB (custom HID)
App/board_config.h            piny, flagi, VID/PID, limity - JEDNO miejsce
App/buttons.c/.h              skanowanie i debounce
App/leds_ws2812.c/.h          PWM+DMA, korekcja GRB, limit prądu
App/oled.c/.h                 interfejs wyświetlacza (na razie stub)
App/protocol.c/.h             parsowanie raportów OUT, budowa raportów IN
App/debug_uart.c/.h           logowanie (znika przy DEBUG_UART_MODE=0)
```

Wymagania na kod:

* wszystkie numery pinów, flagi i limity w `board_config.h`;
* żadnych opóźnień blokujących (`HAL_Delay`) w pętli głównej;
* w obsłudze przerwań tylko ustawianie flag - przetwarzanie w pętli głównej;
* komentarze po polsku, zwięzłe, wyjaśniające **dlaczego**, nie **co**.

---

## 13. Kryteria akceptacji

1. Urządzenie enumeruje się w Windows jako HID **niebędące klawiaturą** -
   wciskanie przycisków nie wpisuje żadnych znaków w aktywnym oknie.
2. `hidapi` po stronie PC otwiera urządzenie i odbiera raporty IN
   (klawiatury są niedostępne dla hidapi - to test, czy klasa jest dobra).
3. Wciśnięcie każdego z 13 przycisków ustawia właściwy bit w raporcie;
   jednoczesne wciśnięcie wszystkich działa bez gubienia zdarzeń.
4. Komenda `0x10` zmienia kolor wskazanej diody w czasie poniżej 10 ms.
5. Komenda `0x11` ustawia wszystkie 13 diod jedną transakcją.
6. Przekroczenie limitu prądu skutkuje proporcjonalnym przyciemnieniem,
   a nie resetem urządzenia.
7. Odłączenie i ponowne podłączenie USB nie wymaga resetu - urządzenie
   enumeruje się ponownie samo.
8. Przy `DEBUG_UART_MODE = 0` wszystkie 13 przycisków działa,
   a na PA2/PA3 nie ma aktywności UART.

---

## 14. Kontrakt z aplikacją MAKKEY (do wiadomości)

Aplikacja na PC (Python + PySide6) będzie po tej zmianie:

* wyszukiwać urządzenie przez `hidapi` po VID/PID oraz
  `usage_page == 0xFF00`;
* czytać raporty IN o ID `0x01` i dekodować bitmapę 13 przycisków;
* wysyłać raporty OUT o ID `0x02` z bajtem komendy wg tabeli z sekcji 7.

Nie zmieniaj numerów Report ID ani układu bajtów bez zaznaczenia tego
wprost - po drugiej stronie jest kod, który się do nich odwołuje.
