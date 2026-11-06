# Kontrola vybavení a instalace

Cíl: na začátku prvního spuštění zjistit, co na počítači funguje, chybějící věci po souhlasu doinstalovat a výsledek zapsat do profilu. Sportovce nezahlcuj – kontrolu dělej potichu a řekni mu jen výsledek a případnou nabídku.

## 1. Co zjistit

Zjisti operační systém (z prostředí, ve kterém běžíš) a postupně vyzkoušej:

| Co | Jak ověřit | K čemu je |
|----|------------|-----------|
| Python ≥ 3.10 | Windows: `py -3 --version`, `python --version`; macOS/Linux: `python3 --version`, `python --version`. Na Windows pozor: `python`, který vypíše „Python was not found… Microsoft Store“ nebo nic nevrátí, **není** Python. | výpočet temp, posílání do hodinek, přehled a grafy, ukládání historie |
| Git | `git --version` | historie změn |
| Knihovna pro Garmin | `<python> -c "import garminconnect, pydantic"` | hodinky a regenerace – zjišťuj jen pokud má sportovec Garmin |
| Strava | jestli jsou dostupné nástroje `mcp__claude_ai_Strava__*` (případně přes ToolSearch) a odpoví `health` / `get_athlete_profile` | automatické načtení závodů a kilometrů |

Jako `<python>` si zapamatuj první příkaz, který funguje (pořadí: Windows `py -3`, `python`; jinde `python3`, `python`). Ten pak používej ve všech příkazech místo `python`.

## 2. Co sportovci říct

Jednou dvěma větami, bez technických slov. Příklady:
- Vše funguje: „Mám vše, co potřebuji – spočítám tempa, pošlu tréninky do hodinek a povedu historii.“
- Chybí Python: „Na počítači chybí program Python, který potřebuji na výpočty, grafy a posílání tréninků do hodinek. Můžu ho teď nainstalovat (zabere to pár minut). Mám?“
- Chybí Git: „Chybí program Git, díky kterému se dá vrátit jakákoli starší verze plánu. Můžu ho nainstalovat?“
- Chybí Strava: „Stravu propojenou nemáte, takže si údaje řekneme – to nevadí.“ (Stravu neinstaluj, propojení je věc nastavení Claude; jen zmiň, že ji lze připojit v nastavení konektorů.)

Instaluj **jen po výslovném souhlasu** a vždy řekni, co a proč instaluješ. Víc chybějících věcí nabídni najednou v jedné otázce.

## 3. Instalace

### Windows
```
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
```
- `--scope user` nepotřebuje administrátora. Git se instaluje pro celý počítač – může vyskočit okno „Chcete povolit změny?“; řekni sportovci předem, že ho má potvrdit.
- Po instalaci aktuální okno nový program nezná. Použij plnou cestu:
  - Python: `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (v Bash: `"$LOCALAPPDATA/Programs/Python/Python312/python.exe"`), případně `py -3`, které funguje hned.
  - Git: `C:\Program Files\Git\cmd\git.exe`.
  Do profilu zapiš funkční příkaz. Pokud plná cesta nefunguje, požádej o restart Claude Code a pokračuj ve vstupním pohovoru – výpočty dokončíš po restartu.
- Není-li `winget` (starší Windows 10): nabídni stažení z https://www.python.org/downloads/ a https://git-scm.com/download/win (při instalaci Pythonu zaškrtnout „Add python.exe to PATH“).

### macOS
- `xcode-select --install` – otevře systémové okno, sportovec potvrdí; přinese Git i Python 3.
- Má-li Homebrew (`brew --version`): `brew install python git`.

### Linux
- Python bývá předinstalovaný. Jinak `sudo apt install -y python3 python3-pip git` (Debian/Ubuntu) nebo `sudo dnf install -y python3 python3-pip git` (Fedora). `sudo` vyžaduje heslo – požádej sportovce, ať příkaz spustí sám (v Claude Code: napsat do promptu `! <příkaz>`).

### Knihovna pro Garmin (všude)
```
<python> -m pip install --user garminconnect pydantic
```
Když pip hlásí „externally-managed-environment“ (novější Linux/macOS s brew), použij `<python> -m pip install --user --break-system-packages garminconnect pydantic`, nebo navrhni samostatné prostředí (`<python> -m venv ~/.trener-venv` a pak používat `~/.trener-venv/bin/python` jako `<python>`).

## 4. Ověření

Po instalaci znovu spusť ověření z kroku 1. Teprve když funguje, považuj věc za dostupnou. Neověřenou instalaci nikdy nehlas jako hotovou.

## 5. Když instalace nejde

Zakázáno (firemní počítač), odmítnuto, nebo chyba:

| Chybí | Náhrada |
|-------|---------|
| Python | tempa z `references/tempa-tabulka.md`; plán, tréninky a textový přehled týdne napiš sám (přehled sestav ručně ve stejném formátu jako `prehled.py text`); bez hodinek, grafů a historie |
| Git | data se ukládají jen do souborů, bez historie a vracení |
| Knihovna pro Garmin | tréninky jen v `treninky.md`; regeneraci se ptej slovně („jak ses vyspal, jak se cítíš“) |
| Strava | údaje a splnění tréninků se ptej ručně |

Sportovci řekni jednou větou, co tím odpadá, a pokračuj. Nabídni, že instalaci lze zkusit kdykoli později („řekni ‚zkus doinstalovat‘“).

## 6. Zápis do profilu

Do `trenink/profil.md`, sekce „Vybavení počítače“:

```markdown
## Vybavení počítače
Ověřeno: 2026-11-04 (Windows 11)
- Python: ano – příkaz `py -3`
- Git: ano
- Garmin: ano (knihovna nainstalovaná, přihlášení OK)
- Strava: ne – údaje zadávány ručně
```

Při dalších spuštěních kontrolu neopakuj – použij zapsané příkazy. Teprve když něco selže, ověř znovu a profil aktualizuj.
