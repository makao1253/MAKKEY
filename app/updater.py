"""Aktualizacje programu z repozytorium na GitHubie.

Tryb zależy od tego, jak MAKKEY jest uruchomiony:

* **z kodu źródłowego** (python main.py w klonie repozytorium) - aktualizacja
  to `git fetch` + `git pull --ff-only`. Git loguje się zapisanymi danymi,
  więc działa to także z prywatnym repozytorium;
* **jako plik exe** (PyInstaller) - aktualizacja to najnowsze wydanie
  (GitHub Releases) z dołączonym MAKKEY.exe. Uruchomionego exe nie da się
  nadpisać, ale da się zmienić jego nazwę - nowy plik wchodzi na jego
  miejsce, a stary znika przy następnym starcie.

API GitHuba dla prywatnego repozytorium wymaga tokenu. Bierzemy go od gita
(`git credential fill`) - to ten sam, którym git loguje się przy push/pull.
Bez gita albo bez zapisanego logowania sprawdzanie działa tylko dla
repozytorium publicznego.

Nic tu nie może zawiesić okna ani wyskoczyć z logowaniem: sieć i git idą
w osobnym wątku, a git dostaje zakaz pytania o hasło.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .constants import APP_VERSION, UPDATE_BRANCH, UPDATE_EXE_ASSET, UPDATE_REPO
from .i18n import tr

MODE_GIT = "git"            # kod źródłowy w klonie repozytorium
MODE_RELEASE = "release"    # plik exe - wydania na GitHubie
MODE_NONE = "none"          # ani jedno, ani drugie - aktualizacja niemożliwa

ROOT = Path(__file__).resolve().parent.parent     # katalog projektu (tryb git)
API_URL = f"https://api.github.com/repos/{UPDATE_REPO}"

_NO_WINDOW = 0x08000000                  # CREATE_NO_WINDOW - bez migającej konsoli
_DETACHED = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
_MAX_CHANGES = 8


class UpdateError(Exception):
    """Aktualizacja się nie udała - treść nadaje się do pokazania w UI."""


@dataclass
class UpdateInfo:
    mode: str
    available: bool
    current: str                      # opis bieżącej wersji
    latest: str                       # opis najnowszej wersji w repozytorium
    changes: list[str] = field(default_factory=list)   # tytuły zmian
    download_url: str = ""            # MODE_RELEASE: adres pliku exe w API


# --------------------------------------------------------------- tryb pracy
def update_mode() -> str:
    if getattr(sys, "frozen", False):
        return MODE_RELEASE
    if (ROOT / ".git").exists() and shutil.which("git"):
        return MODE_GIT
    return MODE_NONE


def _no_prompt_env() -> dict[str, str]:
    """Git bez pytania o hasło - w tle nie ma kogo zapytać."""
    return dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")


def _git(*args: str, timeout: int = 60, cwd: Path | None = ROOT,
         stdin: str | None = None) -> str:
    try:
        done = subprocess.run(
            ["git", *args], cwd=cwd, env=_no_prompt_env(), input=stdin,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, creationflags=_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        raise UpdateError(tr("git nie odpowiedział w ciągu {n} s", n=timeout)) from None
    except OSError as exc:
        raise UpdateError(tr("nie udało się uruchomić gita: {error}", error=exc)) from None
    if done.returncode != 0:
        raise UpdateError(_git_error(done.stderr or done.stdout)
                          or f"git {args[0]}: {done.returncode}")
    return done.stdout.strip()


def _git_error(output: str) -> str:
    """Sedno komunikatu gita: linia "error:"/"fatal:" + wymienione pod nią
    pliki (ostatnia linia to często samo "Aborting")."""
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if line.startswith(("error:", "fatal:")):
            files = [f.strip() for f in lines[i + 1:] if f.startswith(("\t", " "))]
            return " ".join([line.split(":", 1)[1].strip(), ", ".join(files)]).strip()
    return lines[-1] if lines else ""


# ------------------------------------------------------------------ tryb git
def _check_git() -> UpdateInfo:
    _git("fetch", "--quiet", "origin", timeout=90)
    try:
        behind = int(_git("rev-list", "--count", "HEAD..@{u}"))
    except UpdateError:
        raise UpdateError(tr("bieżąca gałąź nie śledzi gałęzi w repozytorium "
                             "(git branch -u origin/{branch})",
                             branch=UPDATE_BRANCH)) from None
    changes = (_git("log", f"-{_MAX_CHANGES}", "--format=%s", "HEAD..@{u}").splitlines()
               if behind else [])
    return UpdateInfo(
        mode=MODE_GIT, available=behind > 0,
        current=f"{APP_VERSION} ({_git('rev-parse', '--short', 'HEAD')})",
        latest=tr("{n} nowych zmian", n=behind) if behind else APP_VERSION,
        changes=changes,
    )


def _install_git():
    # --ff-only: lokalne commity albo zmiany w tych samych plikach zatrzymują
    # aktualizację zamiast robić scalanie za plecami użytkownika.
    _git("pull", "--ff-only", "--quiet", timeout=180)


# -------------------------------------------------------------- tryb wydań
def _github_token() -> str:
    """Token GitHuba zapisany przez gita ('' gdy go nie ma)."""
    if not shutil.which("git"):
        return ""
    try:
        out = _git("credential", "fill", cwd=None, timeout=20,
                   stdin="protocol=https\nhost=github.com\n\n")
    except UpdateError:
        return ""
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    return ""


def _open(url: str, token: str, accept: str = "application/vnd.github+json"):
    request = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": f"MAKKEY/{APP_VERSION}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if token:
        # Nagłówek nie przechodzi przez przekierowanie: plik exe leży na
        # serwerze plików GitHuba, który z tokenem API odrzuca zapytanie.
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(request, timeout=30)


def _version(text: str) -> tuple[int, ...]:
    numbers = [int(n) for n in re.findall(r"\d+", text)[:3]]
    return tuple(numbers + [0] * (3 - len(numbers)))


def _check_release() -> UpdateInfo:
    token = _github_token()
    try:
        with _open(f"{API_URL}/releases/latest", token) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError(
                tr("w repozytorium nie ma jeszcze żadnego wydania (Releases)") if token else
                tr("repozytorium jest prywatne, a git na tym komputerze nie jest "
                   "zalogowany do GitHuba")
            ) from None
        raise

    tag = str(data.get("tag_name", ""))
    asset = next((a for a in data.get("assets", [])
                  if str(a.get("name", "")).lower() == UPDATE_EXE_ASSET.lower()), None)
    newer = _version(tag) > _version(APP_VERSION)
    if newer and asset is None:
        raise UpdateError(tr("wydanie {tag} nie ma dołączonego pliku {name}",
                             tag=tag, name=UPDATE_EXE_ASSET))
    notes = [line.strip("-* ").strip() for line in str(data.get("body") or "").splitlines()]
    return UpdateInfo(
        mode=MODE_RELEASE, available=newer,
        current=APP_VERSION, latest=tag.lstrip("vV") or "?",
        changes=[n for n in notes if n][:_MAX_CHANGES],
        download_url=str(asset.get("url", "")) if asset else "",
    )


def _install_release(info: UpdateInfo, progress) -> None:
    exe = Path(sys.executable)
    new = exe.with_name(exe.name + ".new")
    old = exe.with_name(exe.name + ".old")

    with _open(info.download_url, _github_token(), accept="application/octet-stream") as response, \
            open(new, "wb") as target:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(256 * 1024):
            target.write(chunk)
            done += len(chunk)
            progress(done, total)

    with open(new, "rb") as check:
        header = check.read(2)
    # np. strona błędu zamiast pliku - otwartego pliku Windows nie usunie,
    # więc sprawdzamy dopiero po zamknięciu
    if header != b"MZ" or new.stat().st_size < 1_000_000:
        new.unlink(missing_ok=True)
        raise UpdateError(tr("pobrany plik nie jest programem exe"))

    try:
        old.unlink(missing_ok=True)
        exe.rename(old)
    except OSError as exc:
        new.unlink(missing_ok=True)
        raise UpdateError(tr("nie można podmienić pliku {name}: {error}",
                             name=exe.name, error=exc)) from None
    try:
        new.rename(exe)
    except OSError as exc:
        old.rename(exe)          # stary program wraca na miejsce
        raise UpdateError(tr("nie można podmienić pliku {name}: {error}",
                             name=exe.name, error=exc)) from None


def cleanup_old_exe():
    """Resztki po podmianie exe - do wywołania po starcie nowej wersji."""
    if not getattr(sys, "frozen", False):
        return
    exe = Path(sys.executable)
    for suffix in (".old", ".new"):
        try:
            exe.with_name(exe.name + suffix).unlink(missing_ok=True)
        except OSError:
            pass      # poprzednia instancja jeszcze się zamyka - następnym razem


def start_new_instance():
    """Uruchamia program od nowa (już zaktualizowany) jako osobny proces."""
    if getattr(sys, "frozen", False):
        command, cwd = [sys.executable], Path(sys.executable).parent
    else:
        command, cwd = [sys.executable, str(ROOT / "main.py")], ROOT
    env = dict(os.environ)
    # Nowy exe ma się rozpakować sam, a nie korzystać z katalogu tymczasowego
    # tego procesu, który za chwilę zniknie (PyInstaller --onefile).
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen(command, cwd=cwd, env=env, close_fds=True,
                     creationflags=_DETACHED)


def _describe(exc: Exception) -> str:
    if isinstance(exc, UpdateError):
        return str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        return tr("GitHub zwrócił błąd {code}", code=exc.code)
    if isinstance(exc, urllib.error.URLError):
        return tr("brak połączenia z GitHubem ({error})", error=exc.reason)
    return str(exc) or exc.__class__.__name__


# ------------------------------------------------------------------- wątek
class Updater(QObject):
    """Sprawdza i instaluje aktualizacje w tle, wyniki oddaje sygnałami."""

    checkFinished = Signal(object)      # UpdateInfo
    checkFailed = Signal(str)
    installProgress = Signal(int, int)  # pobrane bajty, całość (0 = nieznana)
    installFinished = Signal()          # gotowe - potrzebny restart programu
    installFailed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = update_mode()
        self.busy = False

    def check(self) -> bool:
        return self._start(self._check_job)

    def install(self, info: UpdateInfo) -> bool:
        return self._start(lambda: self._install_job(info))

    def _start(self, job) -> bool:
        if self.busy or self.mode == MODE_NONE:
            return False
        self.busy = True
        threading.Thread(target=job, daemon=True).start()
        return True

    def _check_job(self):
        try:
            info = _check_git() if self.mode == MODE_GIT else _check_release()
        except Exception as exc:          # noqa: BLE001 - każdy błąd idzie do UI
            self._finish(self.checkFailed, _describe(exc))
        else:
            self._finish(self.checkFinished, info)

    def _install_job(self, info: UpdateInfo):
        try:
            if info.mode == MODE_GIT:
                _install_git()
            else:
                _install_release(info, lambda done, total:
                                 self._emit(self.installProgress, done, total))
        except Exception as exc:          # noqa: BLE001
            self._finish(self.installFailed, _describe(exc))
        else:
            self._finish(self.installFinished)

    def _finish(self, signal, *args):
        self.busy = False
        self._emit(signal, *args)

    @staticmethod
    def _emit(signal, *args):
        try:
            signal.emit(*args)
        except RuntimeError:
            pass      # okno zbudowane od nowa (zmiana języka) - wynik już niepotrzebny
