# Skills pro Claude Code

## bezecky-trener – osobní běžecký trenér

Skill pro [Claude Code](https://claude.com/claude-code), který funguje jako běžecký trenér. Mluví česky a jednoduše, bez technických výrazů.

### Co umí

- **Vstupní pohovor** – cíle sezóny (závody s prioritou A/B/C), osobní rekordy, poslední závod, týdenní objem, omezení. Co jde, předvyplní ze Stravy.
- **Tréninková tempa** – VDOT a tempa E/M/T/I/R z posledního závodu (`scripts/tempa.py`, bez Pythonu tabulka `references/tempa-tabulka.md`).
- **Plán sezóny** – makrocyklus base → build → peak → taper, i pro více závodů v sezóně.
- **Tréninky na 30 dní dopředu** – běžecké i silové, průběžně doplňované.
- **Garmin Connect** – nahrání tréninků do kalendáře a hodinek, čtení wellness (HRV, spánek, Body Battery, Training Readiness) a návrh úprav plánu podle regenerace.
- **Hodnocení tréninků** – kontrola úseků, temp a tepu kvalitních tréninků ze Stravy.
- **Přehled plnění** – textový přehled týdne a grafický dashboard (lokálně i jako soukromá stránka na claude.ai).
- **Historie změn** – každá změna plánu se ukládá do lokálního gitu a dá se vrátit.

### Instalace

Zkopírujte složku `bezecky-trener/` do `.claude/skills/` v projektu (nebo do `~/.claude/skills/` pro všechny projekty). Pak stačí napsat třeba „trenér“, „připrav mi plán na půlmaraton“ nebo „co mám dnes běhat?“.

Při prvním spuštění skill zkontroluje vybavení počítače a chybějící věci po souhlasu doinstaluje (viz `references/vybaveni.md`):

- **Python 3** – výpočty temp, dashboard, Garmin, ukládání,
- **Git** – historie změn plánu,
- **knihovna `garminconnect`** (volitelně) – propojení s Garminem,
- **Strava** (volitelně) – propojený Strava connector v Claude.

Plán jde sestavit i bez nich, jen s omezenými funkcemi.

### Data

Vše se ukládá do složky `trenink/` v pracovním adresáři, ze kterého se Claude Code spouští:

| Soubor | Obsah |
|--------|-------|
| `profil.md` | údaje o sportovci, rekordy, VDOT a tempa, objem, vybavení |
| `plan-sezony.md` | závody a makrocyklus |
| `treninky.md` | konkrétní tréninky po týdnech a jejich plnění |
| `wellness-log.md` | záznam kontrol regenerace |
| `data.json` | data pro přehledy a grafy |
| `dashboard.html` | grafický přehled (funguje offline) |
| `garmin/*.json` | archiv tréninků nahraných do Garminu |

### Struktura skillu

```
bezecky-trener/
├── SKILL.md              # instrukce pro Claude
├── assets/dashboard.html # šablona dashboardu
├── references/           # podklady: periodizace, síla, wellness, hodnocení, tempa, vybavení
└── scripts/
    ├── tempa.py          # VDOT a tréninková tempa
    ├── garmin.py         # Garmin Connect: login, wellness, upload, scheduled, remove, zones
    ├── prehled.py        # textový přehled a HTML dashboard
    └── ulozit.py         # ukládání do historie (git)
```

### Ruční použití skriptů

```bash
python scripts/tempa.py 10k 44:10
python scripts/garmin.py login                 # interaktivní přihlášení (e-mail, heslo, MFA)
python scripts/garmin.py wellness --days 7
python scripts/prehled.py text --data trenink/data.json
python scripts/prehled.py html --data trenink/data.json --out trenink/dashboard.html
```

> Propojení s Garminem používá neoficiální knihovnu `garminconnect`. Přihlašovací údaje se zadávají jen do terminálu, nikdy do chatu.
