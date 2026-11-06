# Hodnocení odběhnutých tréninků

Hodnoť každý **kvalitní trénink** (T, I, R, M / závodní tempo, rovinky, kopce, fartlek) a **dlouhý běh**. Hodnotí se i neplánovaný trénink podobného typu. Lehké běhy hodnoť jen jednou větou, a to jen když je něco zjevně mimo (tep výrazně vysoko, nebo běh výrazně delší či kratší).

Cíl: sportovec ví, **jak se trénink povedl a co příště udělat jinak**. Hodnocení je trenérská zpětná vazba, ne známkování. Pochval, co sedí, a u chyby dej konkrétní radu.

## 1. Data

1. `list_activities` → id aktivity (podle data a typu).
2. `get_activity_performance` → **kola (laps)**: čas, vzdálenost, průměrná rychlost, průměrný a maximální tep, sklon, kadence, watty. Trénink nahraný z hodinek podle plánu má obvykle jedno kolo na každý krok (rozklus, úsek, pauza, …), takže je to hlavní zdroj.
3. **Tepové zóny** – ber je z profilu (sekce Aktuální výkonnost). Zdroj: `garmin.py zones` (hodinky měří tep a zóny počítají z anaerobního prahu, ANP). Když Garmin není, použij `get_athlete_zones` ze Stravy. Pokud se zóny ve Stravě a Garminu liší, platí Garmin a sportovce upozorni, že Strava hodnotí podle jiných zón. Zóny v profilu obnov, když se změní ANP nebo max. tep (Garmin je občas sám upraví).
4. `get_activity_streams` (`time`, `heart_rate`, případně `velocity_smooth` a `grade_smooth`, `resolution` 500–1000) použij, když:
   - kola neodpovídají úsekům (sportovec běžel bez naplánovaného tréninku, jen s automatickým kolem po 1 km). Úseky pak najdi podle prudké změny rychlosti a tepu.
   - potřebuješ **tep na konci pauzy** (průměr kola pauzy to neukáže), nebo tepový drift dlouhého běhu.
5. Porovnej s plánem v `treninky.md` (počet úseků, délka, cílové tempo, délka a typ pauzy) a s tempy v profilu.

Tempo z rychlosti: `min/km = 1000 / rychlost_m_s / 60`. U úseků do ~1 min a v kopcích je GPS tempo nepřesné. Ber ho orientačně a víc váhy dej stejnoměrnosti a tepu. Zohledni sklon (`avg_grade`), vítr a teplotu (počasí je u aktivity).

## 2. Kritéria podle typu

| Typ | Tempo úseků | Stejnoměrnost | Tep v úsecích | Pauza je dostatečná, když… |
|-----|-------------|---------------|---------------|-----------------------------|
| **T** (práh) | T tempo ±5 s/km. Rychleji o > 8 s/km = chyba, T má být kontrolované. | rozdíl nejrychlejšího a nejpomalejšího ≤ 3 % | Z4 dole až uprostřed, mírně stoupá, drift mezi 1. a posledním úsekem ≤ 5 tepů | Krátká pauza je záměr, plné zotavení se nečeká. Na konci pauzy tep klesne o 15–25 tepů. |
| **I** (intervaly) | I tempo ±5 s/km. Úseky do 1 min mohou být o 5–10 s/km rychleji. | poslední úsek stejně rychlý jako první, pokles > 5 % = přepálený začátek nebo krátká pauza | ke konci úseku horní Z4 až Z5 | Na konci pauzy tep klesne aspoň o 30 tepů, nebo do Z2. |
| **R** (rychlost) | R tempo, uvolněně | ≤ 3 % | často nestihne vystoupat, nehodnoť | Úplné zotavení, pauza ≥ 2–3× délka úseku, tep na konci pauzy v Z1–Z2. |
| **M / závodní tempo** | cílové tempo ±3 s/km | ≤ 2 % | stabilní, drift ≤ 5 tepů za úsek | Nižší tep v pauze, ale bez zastavení. |
| **Rovinky** | Tempo nehodnoť. Max rychlost kolem R tempa nebo o trochu rychleji je správně, výrazně rychleji = sprint. | Vidět stupňování (rychlost roste během úseku). | nemají vyletět do Z5 | Před další rovinkou je tep zpět u úrovně lehkého běhu. |
| **Krátké kopce** | Tempo nehodnoť (sklon). Hodnoť stejnoměrnost rychlosti nebo wattů a kadenci. | ≤ 5 % mezi úseky | krátké úseky tep nestihne zvednout, nehodnoť | Úplné zotavení: tep před dalším kopcem zpět u lehkého běhu. |
| **Dlouhý běh** | Podle profilu. Při „na pocit“ jen kontrola, že nebyl rychlejší než E. | Druhá polovina není o > 5 % pomalejší (bez kopců). | Tepový drift (2. polovina vs. 1. při podobném tempu) ≤ 5 % OK, 5–8 % pozor, > 8 % začal moc rychle, horko, málo pití nebo únava. | – |
| **Rozklus / vyklus / klusové pauzy** | lehce | – | Z1–Z2. V Z3 = moc rychle (pozor, únava se sčítá). | – |

Doplňkové signály:
- **Počet úseků** splněn? Chybí-li úseky nebo byly zkrácené, zeptej se proč. Může jít o únavu, čas nebo bolest.
- **Kadence** v úsecích vyšší než v lehkém běhu = dobře. Klesající kadence v posledních úsecích = únava.
- **Opakovaně** výrazně rychlejší než T/I při kontrolovaném tepu = forma roste. Navrhni test nebo přepočet temp, ale plán sám neměň.
- **Opakovaně** nedosažená tempa při vysokém tepu = únava nebo moc ambiciózní tempa. Podívej se na regeneraci (wellness) a zvaž zpomalení temp nebo lehčí týden.

## 3. Výstup pro sportovce

Krátce, česky, trenérsky:

```
Čt 5. 11. – I 5× 1 min, p 2 min klus
| Úsek | Tempo   | Tep prům/max | Tep na konci pauzy |
|------|---------|--------------|--------------------|
| 1    | 4:05/km | 171 / 180    | 142 (−37)          |
| 2    | 4:35/km | 171 / 178    | 138 (−40)          |
…
✓ Pauzy dostatečné – tep vždy spadl o 35–40 tepů.
! První úsek o 30 s/km rychlejší než další → přepálený start; další úseky už pod I tempem (4:22).
→ Příště: první úsek drž na 4:20–4:25, ať jsou všechny stejné.
```

- Tabulka úseků (u rovinek a kopců stačí jeden souhrnný řádek), pak 2–4 body: ✓ co se povedlo, ! na co pozor, → konkrétní rada na příště.
- Odliš, co je ze Stravy a co je tvůj výpočet nebo odhad (tempo krátkých úseků z GPS).
- Nehodnoť přísněji, než data dovolují. Vítr, kopec, kluzký terén a horko řekni nahlas.

## 4. Zápis

- `treninky.md`: do sloupce „Splněno“ krátce (např. `8,2 km ✓ T 4:43/4:45/4:47`). Do řádku „Hodnocení:“ pod tabulkou týdne zapiš jednu větu za každý kvalitní trénink (datum + závěr + rada).
- `data.json` → u dne `skutecnost.zony` podle skutečných úseků a `hodnoceni` jako krátký text (1–2 věty). Dashboard ho ukazuje v kalendáři po najetí na den.
- Opakující se problém (např. 3× po sobě přepálený první úsek, lehké běhy v Z3) zmiň v týdenním souhrnu a při dalším plánování ho promítni do poznámky tréninku v hodinkách (např. „1. úsek nezačínat rychleji!“).
