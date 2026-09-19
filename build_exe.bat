@echo off
rem ============================================================
rem  MAKKEY - budowanie pliku exe jednym dwuklikiem.
rem  Cala robota siedzi w build_exe.py; ten plik tylko znajduje
rem  Pythona, uruchamia go i zostawia okno otwarte z wynikiem.
rem ============================================================
setlocal
cd /d "%~dp0"

echo ============================================
echo   MAKKEY - budowanie pliku exe
echo ============================================
echo.

rem --- znajdz Pythona: najpierw launcher "py", potem "python" ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
    echo [BLAD] Nie znaleziono Pythona.
    echo.
    echo Zainstaluj Pythona 3.10 lub nowszego z https://www.python.org/downloads/
    echo i przy instalacji zaznacz "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo Uzywam: %PY%
echo.
%PY% build_exe.py
set "CODE=%ERRORLEVEL%"

echo.
if "%CODE%"=="0" (
    echo ============================================
    echo   GOTOWE
    echo   Plik: "%~dp0dist\MAKKEY.exe"
    echo ============================================
) else (
    echo ============================================
    echo   BUDOWANIE NIE POWIODLO SIE ^(kod %CODE%^)
    echo   Komunikat bledu jest wypisany powyzej.
    echo ============================================
)

echo.
pause
exit /b %CODE%
