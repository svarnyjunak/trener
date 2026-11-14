"""Přehled tréninku – textový souhrn týdne a HTML dashboard z trenink/data.json.

Použití:
    python prehled.py text [--data trenink/data.json] [--datum 2026-11-12] [--tydnu 4]
    python prehled.py html [--data trenink/data.json] [--out trenink/dashboard.html]
    python prehled.py demo --out <soubor.json>     # vygeneruje ukázková data pro test

Formát data.json:
{
  "atlet": "Jméno",
  "zavody": [{"datum": "2027-04-04", "nazev": "Pražský maraton", "trat": "maraton", "cil": "3:25", "priorita": "A"}],
  "faze":   [{"nazev": "Base", "od": "2026-11-09", "do": "2026-12-20", "objem": "35 → 41",
              "smysl": "Aerobní základ: hodně lehkého běhu, rovinky a krátké kopce."}],
  "dny": [
    {"datum": "2026-11-10", "typ": "run", "nazev": "T 3×5 min",
     "plan": {"km": 8, "min": 45, "zony": {"E": 5, "T": 3}},
     "skutecnost": {"km": 8.2, "min": 44, "zony": {"E": 5.1, "T": 3.1}, "zdroj": "strava"},
     "stav": "splneno", "hodnoceni": "T úseky 4:43–4:47, stejnoměrně, pauzy OK."},
    {"datum": "2026-11-11", "typ": "strength", "nazev": "Síla A", "plan": {"min": 35}, "stav": "splneno"}
  ],
  "wellness": [{"datum": "2026-11-10", "hrv": 52, "rhr": 48, "spanek_h": 7.2, "spanek_skore": 78,
                "bb_rano": 70, "readiness": 66, "hrv_status": "BALANCED", "hrv_dolni": 49}],
  "vdot":   [{"datum": "2026-10-12", "vdot": 46.3, "zdroj": "10 km 44:10"}],
  "upravy": [{"datum": "2026-11-12", "duvod": "HRV LOW 3 dny", "zmena": "I → E 8 km"}]
}
Volitelně u dne "upraveno": "důvod → změna", když se trénink upravil kvůli problému (wellness,
bolest, nemoc) – dashboard ho označí oranžovým růžkem.
Volitelně u dne "popis" a "kroky" (stejný formát jako "steps" v garmin.py) – kompletní trénink do
bublinky v kalendáři. Když chybí, html je doplní z trenink/garmin/*.json podle data a typu.
typ: run | strength | other;  stav: splneno | zkraceno | vynechano | nahrazeno | null (zatím nevyhodnoceno)
zony: km v pásmech E, M, T, I, R (skutečnost je odhad z temp/tepu úseků).
wellness: hrv_status (Garmin) a hrv_dolni (dolní hranice hrv_baseline) jsou volitelné; bez nich se HRV
porovnává s průměrem 28 dní. Dashboard z nich počítá verdikt regenerace podle references/wellness.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ZONY = ["E", "M", "T", "I", "R"]
DNY_CZ = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]


def d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def monday(x: date) -> date:
    return x - timedelta(days=x.weekday())


def load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        sys.exit(f"CHYBA: {p} neexistuje")
    return json.loads(p.read_text(encoding="utf-8"))


VERDICT = ["V pořádku", "Pozor", "Problém"]
VADVICE = ["trénuj podle plánu", "zvaž lehčí den nebo posun kvality", "zvolni – volno nebo jen krátce a lehce"]
VZNAK = ["✓", "!", "✕"]


def wellness_eval(data: dict, today: date) -> list[dict]:
    """Verdikt regenerace po dnech podle references/wellness.md (stejná pravidla jako dashboard).

    l: 0 = v pořádku, 1 = pozor, 2 = problém; sig = jednotlivé ukazatele s textem.
    """
    wl = sorted(data.get("wellness", []), key=lambda x: x["datum"])

    def avg(arr, k):
        v = [a[k] for a in arr if a.get(k) is not None]
        return sum(v) / len(v) if v else None

    def hrv_low(i):
        if wl[i].get("hrv_dolni") is not None:
            return wl[i]["hrv_dolni"]
        prev = [a for a in wl[max(0, i - 28):i] if a.get("hrv") is not None]
        return avg(prev, "hrv") * 0.88 if len(prev) >= 5 else None

    def below(j):
        lo = hrv_low(j)
        return wl[j].get("hrv") is not None and lo is not None and wl[j]["hrv"] < lo

    def rhr_diff(i):
        if i < 0 or wl[i].get("rhr") is None:
            return None
        prev = [a for a in wl[max(0, i - 7):i] if a.get("rhr") is not None]
        return wl[i]["rhr"] - avg(prev, "rhr") if len(prev) >= 3 else None

    def bad_sleep(x):
        return bool(x) and ((x.get("spanek_h") is not None and x["spanek_h"] < 6)
                            or (x.get("spanek_skore") is not None and x["spanek_skore"] < 50))

    out = []
    for i, x in enumerate(wl):
        if d(x["datum"]) > today:
            continue
        sig = []
        r = x.get("readiness")
        if r is not None:
            l = 0 if r >= 60 else 1 if r >= 40 else 2
            sig.append({"k": "Připravenost", "l": l, "t": [f"Připravenost {r} – dobrá",
                        f"Připravenost {r} – střední, tělo se ještě zotavuje", f"Připravenost {r} – nízká"][l]})
        if x.get("hrv") is not None:
            run, j = 0, i
            while j >= 0 and below(j):
                run, j = run + 1, j - 1
            st = (x.get("hrv_status") or "").upper()
            l = 2 if st in ("LOW", "POOR") or run >= 3 else 1 if st == "UNBALANCED" or run >= 1 else 0
            t = (f"HRV {x['hrv']} ms – v tvém normálu" if l == 0
                 else f"HRV pod normálem už {run} noci po sobě ({x['hrv']} ms)" if run >= 3
                 else f"HRV {x['hrv']} ms – pod tvým normálem (obvykle od {round(hrv_low(i))} ms)" if run >= 1
                 else f"HRV nevyrovnaná (Garmin: {st})")
            sig.append({"k": "HRV", "l": l, "t": t})
        s, sc = x.get("spanek_h"), x.get("spanek_skore")
        if s is not None or sc is not None:
            prev = wl[i - 1] if i > 0 else None
            l = (2 if bad_sleep(x) and bad_sleep(prev)
                 else 1 if bad_sleep(x) or (s is not None and s < 7) or (sc is not None and sc < 70) else 0)
            desc = ", ".join(p for p in [f"{s:g} h".replace(".", ",") if s is not None else None,
                                         f"skóre {sc}" if sc is not None else None] if p)
            sig.append({"k": "Spánek", "l": l, "t": [f"Spánek {desc} – dobrý", f"Spánek {desc} – kratší / horší",
                        f"Špatný spánek 2 noci po sobě ({desc})"][l]})
        df = rhr_diff(i)
        if df is not None:
            dp = rhr_diff(i - 1)
            l = 2 if df >= 7 or (df >= 4 and dp is not None and dp >= 4) else 1 if df >= 4 else 0
            sig.append({"k": "Klidový tep", "l": l, "t": f"Klidový tep {x['rhr']} – normální" if l == 0
                        else f"Klidový tep {x['rhr']} – o {round(df)} vyšší než obvykle"
                             + (" (2. den)" if l == 2 and df < 7 else "")})
        bb = x.get("bb_rano")
        if bb is not None:
            l = 0 if bb >= 60 else 1 if bb >= 35 else 2
            sig.append({"k": "Body Battery", "l": l, "t": [f"Body Battery ráno {bb} – nabitý",
                        f"Body Battery ráno jen {bb}", f"Body Battery ráno {bb} – vybitý"][l]})
        reds = sum(1 for g in sig if g["l"] == 2)
        yel = sum(1 for g in sig if g["l"] == 1)
        out.append({"datum": x["datum"], "sig": sig, "l": 2 if reds >= 2 else 1 if reds == 1 or yel >= 2 else 0})
    return out


def phase_of(data: dict, x: date) -> tuple[str | None, int, int]:
    """Vrátí (název fáze, pořadí týdne ve fázi, počet týdnů fáze)."""
    for f in data.get("faze", []):
        a, b = d(f["od"]), d(f["do"])
        if a <= x <= b:
            total = (monday(b) - monday(a)).days // 7 + 1
            idx = (monday(x) - monday(a)).days // 7 + 1
            return f["nazev"], idx, total
    return None, 0, 0


def weeks(data: dict, today: date) -> list[dict]:
    days = data.get("dny", [])
    if not days:
        return []
    by_week: dict[date, list[dict]] = {}
    for x in days:
        by_week.setdefault(monday(d(x["datum"])), []).append(x)
    out = []
    for wk in sorted(by_week):
        items = by_week[wk]
        runs = [x for x in items if x.get("typ", "run") == "run"]
        strength = [x for x in items if x.get("typ") == "strength"]
        sessions = [x for x in items if x.get("typ") != "volno"]
        evaluated = [x for x in sessions if x.get("stav")]
        due = [x for x in sessions if d(x["datum"]) <= today]

        def km(xs, key):
            return round(sum((x.get(key) or {}).get("km") or 0 for x in xs), 1)

        def zones(xs, key):
            z = {k: 0.0 for k in ZONY}
            for x in xs:
                for k, v in ((x.get(key) or {}).get("zony") or {}).items():
                    if k in z:
                        z[k] += v or 0
            return {k: round(v, 1) for k, v in z.items()}

        past_runs = [x for x in runs if d(x["datum"]) <= today]
        name, idx, tot = phase_of(data, wk)
        status = "past" if wk + timedelta(days=6) < today else ("current" if wk <= today else "future")
        out.append({
            "tyden": wk.isoformat(),
            "konec": (wk + timedelta(days=6)).isoformat(),
            "faze": name, "faze_idx": idx, "faze_tot": tot,
            "stav": status,
            "plan_km": km(runs, "plan"),
            "plan_km_dosud": km(past_runs, "plan"),
            "skut_km": km(runs, "skutecnost") if status != "future" else None,
            "plan_zony": zones(runs, "plan"),
            "skut_zony": zones(runs, "skutecnost") if status != "future" else None,
            "plan_dlouhy": max(((x.get("plan") or {}).get("km") or 0 for x in runs), default=0),
            "skut_dlouhy": max(((x.get("skutecnost") or {}).get("km") or 0 for x in runs), default=0)
            if status != "future" else None,
            "treninku": len(sessions), "treninku_dosud": len(due),
            "splneno": sum(1 for x in evaluated if x["stav"] in ("splneno", "nahrazeno")),
            "zkraceno": sum(1 for x in evaluated if x["stav"] == "zkraceno"),
            "vynechano": sum(1 for x in evaluated if x["stav"] == "vynechano"),
            "sila_plan": len(strength),
            "sila_hotovo": sum(1 for x in strength if x.get("stav") in ("splneno", "zkraceno", "nahrazeno")),
        })
    return out


def bar(frac: float, width: int = 10) -> str:
    frac = max(0.0, min(frac, 1.0))
    full = round(frac * width)
    return "▓" * full + "░" * (width - full)


def pct(a, b) -> str:
    return f"{round(100 * a / b)} %" if b else "–"


def next_race(data: dict, today: date):
    races = sorted((r for r in data.get("zavody", []) if d(r["datum"]) >= today), key=lambda r: r["datum"])
    return races[0] if races else None


def cmd_text(a) -> None:
    data = load(a.data)
    today = d(a.datum) if a.datum else date.today()
    ws = weeks(data, today)
    cur = next((w for w in ws if w["tyden"] == monday(today).isoformat()), None)
    lines = []
    if cur:
        head = f"Týden {cur['tyden'][5:]} – {cur['konec'][5:]}"
        if cur["faze"]:
            head += f" | {cur['faze']} {cur['faze_idx']}/{cur['faze_tot']}"
        race = next_race(data, today)
        if race:
            wleft = (d(race["datum"]) - today).days // 7
            head += f" | {wleft} t do {race['nazev']} ({race.get('priorita', '?')})"
        lines.append(head)
        done, plan, plan_now = cur["skut_km"] or 0, cur["plan_km"], cur["plan_km_dosud"]
        lines.append(f"Objem      {bar(done / plan if plan else 0)}  {done:g} / {plan:g} km"
                     f"  (dosud plán {plan_now:g} km → {pct(done, plan_now)})")
        lines.append(f"Tréninky   {cur['splneno']}/{cur['treninku_dosud']} splněno"
                     + (f" · {cur['zkraceno']} zkráceno" if cur["zkraceno"] else "")
                     + (f" · {cur['vynechano']} vynecháno" if cur["vynechano"] else "")
                     + f" · síla {cur['sila_hotovo']}/{cur['sila_plan']}"
                     + f"  (týden celkem {cur['treninku']})")
        pz, sz = cur["plan_zony"], cur["skut_zony"] or {}
        fmt = lambda z: " · ".join(f"{k} {z.get(k, 0):g}" for k in ZONY if z.get(k))  # noqa: E731
        q_plan = sum(pz[k] for k in ZONY[1:])
        q_share = round(100 * q_plan / plan) if plan else 0
        lines.append(f"Intenzita  plán {fmt(pz) or '–'} km  (kvalita {q_share} %)")
        if sz and any(sz.values()):
            lines.append(f"           skutečnost {fmt(sz)} km")
        lr = f"Dlouhý běh plán {cur['plan_dlouhy']:g} km"
        if cur["skut_dlouhy"]:
            lr += f", zaběhnuto {cur['skut_dlouhy']:g} km"
        lines.append(lr)
    else:
        lines.append(f"Pro týden od {monday(today)} nejsou v data.json žádné tréninky.")

    ev = wellness_eval(data, today)
    if ev:
        last = ev[-1]
        age = (today - d(last["datum"])).days
        lines.append(f"Regenerace {VERDICT[last['l']]} – {VADVICE[last['l']]}  [{last['datum'][5:]}]")
        if age >= 2:
            lines.append(f"           pozor: poslední data z hodinek jsou {age} dny stará")
        for s in sorted((s for s in last["sig"] if s["l"] > 0), key=lambda s: -s["l"]):
            lines.append(f"           {VZNAK[s['l']]} {s['t']}")
        by = {x["datum"]: x for x in ev}
        days14 = [(today - timedelta(days=13 - k)).isoformat() for k in range(14)]
        strip = "".join(VZNAK[by[x]["l"]] if x in by else "·" for x in days14)
        cnt = [sum(1 for x in days14 if x in by and by[x]["l"] == l) for l in range(3)]
        lines.append(f"           14 dní {strip}  ({cnt[0]}× ok · {cnt[1]}× pozor · {cnt[2]}× problém)")

    past = [w for w in ws if w["stav"] == "past"][-a.tydnu:]
    if past:
        lines.append("Předchozí týdny:")
        for w in past:
            p, s = w["plan_km"], w["skut_km"] or 0
            lines.append(f"  {w['tyden'][5:]}  {bar(s / p if p else 0)}  {s:g} / {p:g} km  {pct(s, p):>6}"
                         f"  {w['faze'] or ''}")
    print("\n".join(lines))


def garmin_workouts(folder: Path) -> dict:
    """Tréninky z trenink/garmin/*.json podle (datum, typ); novější soubor (oprava) přepíše starší."""
    out: dict = {}
    for f in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for w in items if isinstance(items, list) else []:
            if isinstance(w, dict) and w.get("date") and w.get("steps"):
                out.setdefault((w["date"], w.get("type", "run")), {})[w.get("name", "")] = w
    return out


def with_workouts(days: list, folder: Path) -> list:
    """Ke dnům připojí kompletní trénink (popis + kroky) pro tooltip dashboardu."""
    gw = garmin_workouts(folder) if folder.is_dir() else {}
    out = []
    for x in days:
        x = dict(x)
        if "kroky" not in x:
            cand = gw.get((x["datum"], x.get("typ") or "run"), {})
            w = cand.get(x.get("nazev", "")) or (list(cand.values())[-1] if cand else None)
            if w:
                x["kroky"] = w["steps"]
                if w.get("description") and "popis" not in x:
                    x["popis"] = w["description"]
        out.append(x)
    return out


def cmd_html(a) -> None:
    data = load(a.data)
    today = date.today()
    payload = {
        "dnes": today.isoformat(),
        "cas": datetime.now().strftime("%H:%M"),
        "atlet": data.get("atlet", ""),
        "tydny": weeks(data, today),
        "dny": with_workouts(data.get("dny", []), Path(a.data).parent / "garmin"),
        "zavody": data.get("zavody", []),
        "faze": data.get("faze", []),
        "wellness": sorted(data.get("wellness", []), key=lambda x: x["datum"]),
        "vdot": sorted(data.get("vdot", []), key=lambda x: x["datum"]),
        "upravy": sorted(data.get("upravy", []), key=lambda x: x["datum"], reverse=True),
    }
    tpl = (Path(__file__).parent.parent / "assets" / "dashboard.html").read_text(encoding="utf-8")
    js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = tpl.replace("/*__DATA__*/null", js)
    if a.artifact:
        # stránka na claude.ai dostane kostru dokumentu sama – odstraň vlastní obal
        for tag in ('<!doctype html>', '<html lang="cs">', '<head>', '<meta charset="utf-8">',
                    '<meta name="viewport" content="width=device-width, initial-scale=1">',
                    '</head>', '<body>', '</body>', '</html>'):
            page = page.replace(tag + "\n", "", 1).replace(tag, "", 1)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"Dashboard uložen: {out.resolve()}")


def cmd_demo(a) -> None:
    """Ukázková data: 6 týdnů base (4 za námi), wellness, závod."""
    import random
    random.seed(4)
    today = date.today()
    start = monday(today) - timedelta(weeks=4)
    vols = [32, 35, 38, 28, 38, 41, 44, 33, 44, 47]
    dny, wl = [], []
    for wi, vol in enumerate(vols):
        wk = start + timedelta(weeks=wi)
        lr = round(vol * 0.32)
        q = 0 if wi < 2 else 3 + (wi % 2)
        tue, wed = round((vol - lr - q - 4) * 0.4), round((vol - lr - q - 4) * 0.3)
        sat = vol - lr - q - 4 - tue - wed
        plan = [  # (den, typ, název, km, zóny)
            (1, "run", "E + rovinky", tue, {"E": tue}),
            (1, "strength", "Síla A", 0, {}),
            (2, "run", "E", wed, {"E": wed}),
            (3, "run", f"T {q} km" if q else "E", q + 4, {"E": 4, "T": q} if q else {"E": 4}),
            (4, "strength", "Síla A", 0, {}),
            (5, "run", "E", sat, {"E": sat}),
            (6, "run", "Dlouhý E", lr, {"E": lr}),
        ]
        for off, typ, name, km, z in plan:
            day = wk + timedelta(days=off)
            item = {"datum": day.isoformat(), "typ": typ, "nazev": name,
                    "plan": {"km": km, "zony": z} if typ == "run" else {"min": 35}}
            if day < today:
                r = random.random()
                stav = "vynechano" if r < 0.08 else ("zkraceno" if r < 0.22 else "splneno")
                item["stav"] = stav
                if typ == "run" and stav != "vynechano":
                    f = 1.0 if stav == "splneno" else 0.7
                    item["skutecnost"] = {"km": round(km * f * random.uniform(0.97, 1.05), 1),
                                          "zony": {k: round(v * f, 1) for k, v in z.items()}, "zdroj": "strava"}
            dny.append(item)
    for i in range(28, 0, -1):
        day = today - timedelta(days=i)
        wl.append({"datum": day.isoformat(), "hrv": round(random.gauss(54, 4)), "rhr": round(random.gauss(48, 1.5)),
                   "spanek_h": round(random.uniform(5.8, 8.2), 1), "readiness": round(random.uniform(35, 85))})
    data = {
        "atlet": "Ukázka",
        "zavody": [{"datum": (start + timedelta(weeks=9, days=6)).isoformat(), "nazev": "Jarní půlmaraton",
                    "trat": "pulmaraton", "cil": "1:38", "priorita": "B"},
                   {"datum": (start + timedelta(weeks=20, days=6)).isoformat(), "nazev": "Pražský maraton",
                    "trat": "maraton", "cil": "3:25", "priorita": "A"}],
        "faze": [{"nazev": "Base", "od": start.isoformat(), "do": (start + timedelta(weeks=6, days=-1)).isoformat()},
                 {"nazev": "Build", "od": (start + timedelta(weeks=6)).isoformat(),
                  "do": (start + timedelta(weeks=13, days=-1)).isoformat()}],
        "dny": dny, "wellness": wl,
        "vdot": [{"datum": (start - timedelta(days=20)).isoformat(), "vdot": 45.8, "zdroj": "10 km 44:30"},
                 {"datum": (start + timedelta(days=17)).isoformat(), "vdot": 46.3, "zdroj": "10 km 44:10"}],
        "upravy": [{"datum": (today - timedelta(days=5)).isoformat(), "duvod": "HRV pod baseline 3 dny",
                    "zmena": "I 5×1000 m → E 8 km"}],
    }
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Ukázková data: {a.out}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Přehled tréninku")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("text")
    t.add_argument("--data", default="trenink/data.json")
    t.add_argument("--datum")
    t.add_argument("--tydnu", type=int, default=4)
    t.set_defaults(fn=cmd_text)
    h = sub.add_parser("html")
    h.add_argument("--data", default="trenink/data.json")
    h.add_argument("--out", default="trenink/dashboard.html")
    h.add_argument("--artifact", action="store_true", help="verze pro soukromou stránku na claude.ai")
    h.set_defaults(fn=cmd_html)
    m = sub.add_parser("demo")
    m.add_argument("--out", required=True)
    m.set_defaults(fn=cmd_demo)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
