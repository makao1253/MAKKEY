@echo off
rem ============================================================
rem  MAKKEY - wyslanie zmian do repozytorium na GitHubie.
rem  Cala robota siedzi w aktualizuj_repo.py; ten plik tylko
rem  znajduje Pythona, uruchamia go i zostawia okno z wynikiem.
rem ============================================================
setlocal
cd /d "%~dp0"

echo ============================================
echo   MAKKEY - aktualizacja repozytorium
echo ============================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Nie znaleziono gita.
    echo.
    echo Zainstaluj Git for Windows z https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

rem --- znajdz Pythona: najpierw launcher "py", potem "python" ---
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
    echo [BLAD] Nie znaleziono Pythona.
    echo.
    pause
    exit /b 1
)

%PY% aktualizuj_repo.py %*
set "CODE=%ERRORLEVEL%"

echo.
if not "%CODE%"=="0" (
    echo ============================================
    echo   NIE UDALO SIE ^(kod %CODE%^)
    echo   Komunikat bledu jest wypisany powyzej.
    echo ============================================
    echo.
)
pause
exit /b %CODE%
