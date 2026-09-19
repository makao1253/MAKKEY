"""Wysyłanie zmian do repozytorium na GitHubie.

Uruchomienie - dowolne z dwóch:
    aktualizuj_repo.bat                  (dwuklik w Eksploratorze)
    python aktualizuj_repo.py ["opis zmian"]

Skrypt pokazuje zmienione pliki, pyta o opis zmian, robi commit wszystkiego
i wysyła go na serwer (push). Gdy na serwerze są zmiany z innego komputera,
najpierw je dociąga (pull --rebase) - inaczej push zostałby odrzucony.

Plik exe nie trafia do repozytorium (dist/ jest w .gitignore). Nowy
MAKKEY.exe publikuje się jako wydanie (Releases) na GitHubie - patrz README.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REMOTE = "origin"


def git(*args: str, check: bool = True, capture: bool = True) -> str:
    """Polecenie git w katalogu projektu. capture=False pokazuje wyjście na
    bieżąco (logowanie, konflikty) zamiast je przechwytywać."""
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace",
        capture_output=capture,
    )
    if check and result.returncode != 0:
        if capture:
            print((result.stderr or result.stdout).strip())
        raise SystemExit(f"\n[BŁĄD] git {' '.join(args)} - kod {result.returncode}")
    return (result.stdout or "").strip() if capture else ""


def main() -> int:
    if not (ROOT / ".git").exists():
        print(f"[BŁĄD] {ROOT} nie jest repozytorium git.")
        return 1
    remote_url = git("remote", "get-url", REMOTE, check=False)
    if not remote_url:
        print(f"[BŁĄD] Brak zdalnego repozytorium \"{REMOTE}\".\n"
              f"Dodaj je:  git remote add {REMOTE} https://github.com/<konto>/MAKKEY.git")
        return 1
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    print(f"Repozytorium: {remote_url}\nGałąź:        {branch}\n")

    # --- commit ---
    changes = git("status", "--short")
    if changes:
        print("Zmienione pliki:")
        print(changes)
        print()
        message = " ".join(sys.argv[1:]).strip()
        if not message:
            message = input("Opis zmian (Enter = opis domyślny): ").strip()
        if not message:
            message = f"Aktualizacja {datetime.now():%Y-%m-%d %H:%M}"
        git("add", "--all")
        git("commit", "--quiet", "-m", message)
        print(f"[commit] {message}")
    else:
        print("Brak nowych zmian w plikach.")

    # --- zmiany z serwera (np. z innego komputera) ---
    on_server = bool(git("ls-remote", "--heads", REMOTE, branch))
    if on_server:
        print("[pull] pobieram zmiany z serwera...")
        try:
            git("pull", "--rebase", "--quiet", REMOTE, branch, capture=False)
        except SystemExit:
            print("\nZmiany z serwera kolidują z lokalnymi. Rozwiąż konflikty\n"
                  "(git status pokaże pliki), potem: git rebase --continue\n"
                  "i uruchom ten skrypt ponownie.")
            raise
        ahead = int(git("rev-list", "--count", f"{REMOTE}/{branch}..HEAD"))
    else:
        ahead = int(git("rev-list", "--count", "HEAD"))

    # --- push ---
    if ahead == 0:
        print("\nRepozytorium na serwerze jest aktualne - nie ma czego wysyłać.")
        return 0
    print(f"[push] wysyłam commity: {ahead}")
    git("push", "--set-upstream", REMOTE, branch, capture=False)
    print(f"\nGotowe: {remote_url.removesuffix('.git')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
