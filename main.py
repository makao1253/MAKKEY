"""Punkt wejścia aplikacji MAKKEY.
#define BOARD_BUTTON_TABLE                       \
  { GPIOA,     GPIO_PIN_7  },  /* BTN1  PA7  */  \
  { GPIOA,     GPIO_PIN_4  },  /* BTN2  PA4  */  \
  { GPIOA,     GPIO_PIN_0  },  /* BTN3  PA0  */  \
  { GPIOB,     GPIO_PIN_6  },  /* BTN4  PB6  */  \
  { GPIOF,     GPIO_PIN_1  },  /* BTN5  PF1  */  \
  { GPIOA,     GPIO_PIN_1  },  /* BTN6  PA1  */  \
  { GPIOA,     GPIO_PIN_3  },  /* BTN7  PA3  - kolizja z USART2_RX */ \
  { GPIOA,     GPIO_PIN_6  },  /* BTN8  PA6  */  \
  { GPIOA,     GPIO_PIN_5  },  /* BTN9  PA5  */  \
  { GPIOA,     GPIO_PIN_2  },  /* BTN10 PA2  - kolizja z USART2_TX */ \
  { BTN11_PORT, BTN11_PIN  },  /* BTN11 PA10 */  \
  { GPIOF,     GPIO_PIN_0  },  /* BTN12 PF0  */  \
  { GPIOB,     GPIO_PIN_5  }   /* BTN13 PB5  - zmiana profilu */
  
Uruchomienie:
    pip install -r requirements.txt
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from app.constants import APP_NAME, APP_VERSION
from app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    # Program żyje dalej po schowaniu okna do zasobnika - bez tego Qt zamknęłoby
    # go przy zniknięciu ostatniego okna i macropad przestałby działać.
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
