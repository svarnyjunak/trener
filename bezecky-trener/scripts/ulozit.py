"""Ukládání tréninkových dat do historie (git) – jednoduché hlášky pro sportovce.

Použití:
    python ulozit.py "Popis změny"            # uloží vše ve složce trenink/ (při prvním použití založí historii)
    python ulozit.py "Popis" --dir trenink
    python ulozit.py --historie [-n 10]       # posledních N uložení

Historie je jen lokální (nic se nikam neodesílá). Pokud složka leží uvnitř existujícího
git repozitáře, použije se ten a ukládají se jen soubory ze složky s daty.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

GITIGNORE = ("# dočasné soubory\n*.tmp\n*.bak\n__pycache__/\n"
             "# verze přehledu pro claude.ai (generuje se z data.json)\n.web/\n")


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", check=check)


def ensure_repo(d: Path) -> None:
    if git(d, "rev-parse", "--is-inside-work-tree", check=False).returncode == 0:
        return
    git(d, "init", "-q")
    git(d, "symbolic-ref", "HEAD", "refs/heads/main", check=False)
    gi = d / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8")
    print(f"Založil jsem historii změn ve složce {d}.")


def identity_args(d: Path) -> list[str]:
    """Když není nastavené jméno pro git, použij neutrální jen pro tento zápis."""
    name = git(d, "config", "user.name", check=False).stdout.strip()
    mail = git(d, "config", "user.email", check=False).stdout.strip()
    args = []
    if not name:
        args += ["-c", "user.name=Běžecký trenér"]
    if not mail:
        args += ["-c", "user.email=trener@localhost"]
    return args


def save(d: Path, message: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    ensure_repo(d)
    gi = d / ".gitignore"
    if gi.exists() and ".web/" not in gi.read_text(encoding="utf-8").split():
        with gi.open("a", encoding="utf-8") as f:
            f.write("\n.web/\n")
        git(d, "rm", "-r", "-q", "--cached", "--ignore-unmatch", ".web", check=False)
    git(d, "add", "-A", "--", ".")
    if git(d, "diff", "--cached", "--quiet", "--", ".", check=False).returncode == 0:
        print("Nic nového k uložení.")
        return
    # Vlastní historie složky: uložit celý připravený stav (včetně vyřazených souborů).
    # Složka uvnitř cizího repozitáře: uložit jen tuto složku, ať se nepřibalí nic dalšího.
    top = Path(git(d, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    scope = [] if top == d.resolve() else ["--", "."]
    res = subprocess.run(["git", *identity_args(d), "commit", "-q", "-m", message, *scope],
                         cwd=d, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(f"Uložení se nepovedlo: {res.stderr.strip() or res.stdout.strip()}", file=sys.stderr)
        sys.exit(1)
    print(f"Uloženo: {message}")


def history(d: Path, n: int) -> None:
    if not d.exists() or git(d, "rev-parse", "--is-inside-work-tree", check=False).returncode != 0:
        print("Historie zatím neexistuje.")
        return
    out = git(d, "log", f"-n{n}", "--date=format:%d.%m.%Y %H:%M", "--format=%ad  %s", "--", ".",
              check=False).stdout.strip()
    print(out or "Historie je zatím prázdná.")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not shutil.which("git"):
        sys.exit("Na počítači chybí program Git, bez něj nejde historii ukládat. "
                 "Stáhnout ho lze z https://git-scm.com/download/win")
    p = argparse.ArgumentParser(description="Uložení tréninkových dat do historie")
    p.add_argument("zprava", nargs="?")
    p.add_argument("--dir", default="trenink")
    p.add_argument("--historie", action="store_true")
    p.add_argument("-n", type=int, default=10)
    a = p.parse_args()
    d = Path(a.dir).resolve()
    if a.historie:
        history(d, a.n)
    elif a.zprava:
        save(d, a.zprava)
    else:
        p.error("chybí popis změny")


if __name__ == "__main__":
    main()
