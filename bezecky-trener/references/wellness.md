# Wellness z Garminu – vyhodnocení a úprava tréninku

Data: `python scripts/garmin.py wellness --days 7` (JSON po dnech). Hodnoty jsou z hodinek, ne lékařská diagnóza – vždy je porovnávej s tím, jak se sportovec cítí, a ber v úvahu trend (3+ dny), ne jednu noc.

## Signály

| Ukazatel | Zelená | Žlutá | Červená |
|----------|--------|-------|---------|
| Training Readiness | ≥ 60 (HIGH/PRIME) | 40–59 (MODERATE) | < 40 (LOW/POOR) |
| HRV status | BALANCED | UNBALANCED, nebo noc pod `hrv_baseline` dolní hranicí | LOW / POOR, nebo ≥ 3 noci pod baseline |
| Spánek | ≥ 7 h, skóre ≥ 70 | 6–7 h nebo skóre 50–69 | < 6 h nebo skóre < 50, 2+ noci po sobě |
| Klidový tep | do +3 tepy nad 7denním průměrem | +4–6 | ≥ +7, nebo zvýšený 2+ dny |
| Body Battery ráno | ≥ 60 | 35–59 | < 35 |
| ACWR (akutní/chronická zátěž) | 0,8–1,3 (OPTIMAL) | 1,3–1,5 (HIGH) | > 1,5 (VERY HIGH) |
| Stres průměr | < 35 | 35–50 | > 50 |

Chybějící hodnoty (hodinky nebyly v noci na ruce, model je nepodporuje) ignoruj a řekni to.

## Rozhodovací pravidla

Vyhodnocuj **dnešek a nejbližší 2–3 dny plánu**:

1. **Vše zelené / max 1 žlutá** → beze změny.
2. **2+ žluté, nebo 1 červená** (bez nemoci):
   - kvalitní trénink dnes/zítra → posuň o 1–2 dny (pokud to týden dovolí), nebo zjednoduš (I → T, T → steady E, zkrátit o 25–30 %),
   - dlouhý běh → zkrátit o 20–30 %, jen E,
   - silový trénink → udržovací verze nebo vynechat plyometrii.
3. **2+ červené, nebo červená HRV/readiness trvající 3+ dny** → 1–2 dny volno nebo jen 30–40 min velmi lehce; zbytek týdne bez I úseků; zvaž odlehčený týden dřív.
4. **ACWR > 1,5** → nezvyšuj objem další týden, zařaď odlehčení.
5. **Příznaky nemoci** (horečka, bolest v krku + zvýšený klidový tep) → žádný běh, dokud příznaky neodezní; nad krkem lehce max. Postup návratu viz `periodizace.md` sekce 6.
6. **Dlouhodobě výborné hodnoty + sportovec hlásí, že tempa jsou snadná** → můžeš navrhnout test / přepočet VDOT, ne přidávat objem nad plán.

Před závodem (taper) buď opatrnější s odebíráním – únava v taperu je často jen přechodná a krátké ostré úseky se nechávají.

## Jak navrhnout úpravu

- Ukaž stručnou tabulku posledních dní (spánek, HRV, readiness, klidový tep, BB) a jednou větou interpretaci.
- Navrhni konkrétní změnu (co, kdy, proč) a **zeptej se, zda ji provést** – sportovec ví, jestli byla špatná noc kvůli dítěti nebo kvůli nemoci.
- Po souhlasu: uprav `treninky.md`, poznamenej důvod (např. „↓ HRV LOW 3 dny“), a změněné dny přenahraj do Garminu (`remove` pro dané datum + `upload` nové verze).
- Zapiš stručný záznam do `trenink/wellness-log.md` (datum, klíčové hodnoty, rozhodnutí) – pomůže to vidět trendy.
