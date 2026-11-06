"""Garmin Connect pro běžeckého trenéra – wellness, nahrávání a plánování tréninků.

Používá neoficiální knihovnu `garminconnect` (pip install garminconnect pydantic).
Tokeny se ukládají do ~/.garminconnect (lze změnit proměnnou GARMINTOKENS).

Příkazy:
    python garmin.py login                         # jednorázové přihlášení (interaktivní, MFA)
    python garmin.py wellness [--days 7] [--raw]   # souhrn spánku, HRV, Body Battery, readiness...
    python garmin.py upload <soubor.json> [--dry-run]   # vytvoří tréninky a naplánuje je do kalendáře
    python garmin.py scheduled --from 2026-11-01 --to 2026-12-15   # naplánované tréninky v kalendáři
    python garmin.py remove --from 2026-11-10 --to 2026-12-15 [--dry-run]
                                                   # smaže z kalendáře i knihovny jen tréninky skillu
    python garmin.py exercise <hledaný text>       # vyhledá cvik v katalogu Garminu
    python garmin.py zones                         # tepové zóny, max tep a anaerobní práh z Garminu

Tréninky vytvořené skillem mají v názvu prefix PREFIX, podle něj je `remove` pozná
a nikdy nesahá na tréninky, které si uživatel vytvořil sám.

Formát vstupního JSON pro `upload` (seznam tréninků):
[
  {"date": "2026-11-10", "type": "run", "name": "Prahový 3×5 min",
   "description": "Rozklus, 3×5 min T, vyklus",
   "steps": [
     {"kind": "warmup", "distance_km": 2, "pace": "5:12-6:00"},
     {"kind": "repeat", "times": 3, "steps": [
        {"kind": "interval", "time": "5:00", "pace": "4:32"},
        {"kind": "recovery", "time": "1:00"}]},
     {"kind": "cooldown", "distance_km": 2}
   ]},
  {"date": "2026-11-11", "type": "strength", "name": "Síla A",
   "steps": [
     {"exercise": "Goblet Squat", "sets": 3, "reps": 10, "rest": "1:30", "weight_kg": 16},
     {"exercise": "Side Plank", "sets": 2, "time": "0:40", "rest": "0:30"}
   ]}
]
Běžecké kroky: kind = warmup | interval | recovery | cooldown | repeat;
konec kroku = "time" (m:ss), "distance_km" nebo nic (tlačítko Lap);
cíl = "pace" ("4:32" -> pásmo ±5 s, nebo "4:28-4:36") nebo "hr_zone" (1–5);
"note" = krátký text zobrazený u kroku na hodinkách (např. popis intenzity).
Silové kroky: "exercise" = přesný anglický název z katalogu (viz `exercise`),
nebo "KATEGORIE/CVIK"; "reps" nebo "time"; "rest"; volitelně "weight_kg".
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from getpass import getpass
from pathlib import Path

PREFIX = "[Trenér] "
TOKENSTORE = os.getenv("GARMINTOKENS", str(Path("~/.garminconnect").expanduser()))


# ---------------------------------------------------------------- pomocné funkce

def die(msg: str) -> None:
    print(f"CHYBA: {msg}", file=sys.stderr)
    sys.exit(1)


def import_lib():
    try:
        import garminconnect  # noqa: F401
        from garminconnect import workout  # noqa: F401
        import pydantic  # noqa: F401
    except ImportError:
        die("Chybí knihovna. Nainstaluj: pip install garminconnect pydantic")
    import garminconnect
    return garminconnect


def connect():
    gc = import_lib()
    api = gc.Garmin()
    try:
        api.login(TOKENSTORE)
    except Exception as e:  # noqa: BLE001
        die(f"Nepodařilo se přihlásit tokeny z {TOKENSTORE} ({e}). "
            "Spusť nejdřív: python garmin.py login")
    return api


def secs(s: str | int | float) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    parts = [float(p) for p in str(s).split(":")]
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


def pace_to_speed(p: str) -> float:
    """'4:32' (min/km) -> m/s"""
    return 1000.0 / secs(p)


def pace_target(p: str) -> dict:
    if "-" in p:
        a, b = (x.strip() for x in p.split("-", 1))
        fast, slow = sorted([secs(a), secs(b)])
    else:
        fast, slow = secs(p) - 5, secs(p) + 5
    return {
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone", "displayOrder": 6},
        "targetValueOne": round(1000.0 / slow, 4),   # pomalejší hranice (nižší m/s)
        "targetValueTwo": round(1000.0 / fast, 4),   # rychlejší hranice
    }


def hr_target(zone: int) -> dict:
    return {
        "targetType": {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone", "displayOrder": 4},
        "zoneNumber": int(zone),
    }


# ---------------------------------------------------------------- stavba tréninků

STEP_TYPES = {
    "warmup": (1, "warmup"), "cooldown": (2, "cooldown"), "interval": (3, "interval"),
    "recovery": (4, "recovery"), "rest": (5, "rest"),
}


class Builder:
    def __init__(self):
        self.order = 0
        self.est = 0.0  # odhad trvání v s

    def next(self) -> int:
        self.order += 1
        return self.order

    def run_step(self, st: dict, default_pace_s: float = 360.0) -> dict:
        from garminconnect.workout import ExecutableStep

        kind = st.get("kind", "interval")
        if kind == "repeat":
            return self.repeat(st)
        if kind not in STEP_TYPES:
            raise ValueError(f"neznámý typ kroku: {kind}")
        tid, tkey = STEP_TYPES[kind]
        step: dict = {
            "stepOrder": self.next(),
            "stepType": {"stepTypeId": tid, "stepTypeKey": tkey, "displayOrder": tid},
        }
        pace_s = default_pace_s
        if "pace" in st:
            pace_s = secs(st["pace"].split("-")[0])
        if "time" in st:
            step["endCondition"] = {"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": True}
            step["endConditionValue"] = secs(st["time"])
            self.est += secs(st["time"])
        elif "distance_km" in st:
            step["endCondition"] = {"conditionTypeId": 3, "conditionTypeKey": "distance", "displayOrder": 3, "displayable": True}
            step["endConditionValue"] = float(st["distance_km"]) * 1000
            self.est += float(st["distance_km"]) * pace_s
        else:
            step["endCondition"] = {"conditionTypeId": 1, "conditionTypeKey": "lap.button", "displayOrder": 1, "displayable": True}
        if "pace" in st:
            step.update(pace_target(st["pace"]))
        elif "hr_zone" in st:
            step.update(hr_target(st["hr_zone"]))
        else:
            step["targetType"] = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1}
        if "note" in st:
            step["description"] = st["note"]
        return ExecutableStep(**step)

    def repeat(self, st: dict):
        from garminconnect.workout import create_repeat_group

        order = self.next()
        before = self.est
        inner = [self.run_step(s) for s in st["steps"]]
        one = self.est - before
        self.est += one * (int(st["times"]) - 1)
        return create_repeat_group(int(st["times"]), inner, order)

    def strength_step(self, st: dict):
        from garminconnect import exercises
        from garminconnect.workout import (ExecutableStep, create_repeat_group,
                                           create_strength_exercise_step, create_strength_rest_step)

        name = st["exercise"]
        if "/" in name:
            cat, ex = name.split("/", 1)
        else:
            hit = exercises.resolve(name)
            if not hit:
                alts = [e["name"] for e in exercises.find(name)][:8]
                raise ValueError(f"cvik '{name}' není v katalogu. Podobné: {alts}")
            cat, ex = hit["category"], hit["exercise"]

        sets = int(st.get("sets", 1))
        rest = secs(st.get("rest", 60))
        group_order = self.next()
        ex_order, rest_order = self.next(), self.next()
        if "reps" in st:
            ex_step = create_strength_exercise_step(cat, ex_order, int(st["reps"]), exercise_name=ex,
                                                    weight_kg=st.get("weight_kg"))
            work = int(st["reps"]) * 3
        else:
            work = secs(st["time"])
            ex_step = ExecutableStep(
                stepOrder=ex_order,
                stepType={"stepTypeId": 3, "stepTypeKey": "interval", "displayOrder": 3},
                endCondition={"conditionTypeId": 2, "conditionTypeKey": "time", "displayOrder": 2, "displayable": True},
                endConditionValue=work,
                targetType={"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target", "displayOrder": 1},
                category=cat, exerciseName=ex,
            )
        if "note" in st:
            ex_step.description = st["note"]  # type: ignore[attr-defined]
        self.est += sets * (work + rest)
        return create_repeat_group(sets, [ex_step, create_strength_rest_step(rest, rest_order)], group_order)


def build_workout(w: dict):
    from garminconnect.workout import RunningWorkout, StrengthWorkout, WorkoutSegment

    b = Builder()
    kind = w.get("type", "run")
    name = PREFIX + w["name"]
    if kind == "run":
        steps = [b.run_step(s) for s in w["steps"]]
        sport = {"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1}
        cls = RunningWorkout
    elif kind == "strength":
        steps = [b.strength_step(s) for s in w["steps"]]
        sport = {"sportTypeId": 5, "sportTypeKey": "strength_training", "displayOrder": 5}
        cls = StrengthWorkout
    else:
        raise ValueError(f"neznámý typ tréninku: {kind}")
    return cls(
        workoutName=name[:80],
        estimatedDurationInSecs=int(b.est),
        description=w.get("description"),
        workoutSegments=[WorkoutSegment(segmentOrder=1, sportType=sport, workoutSteps=steps)],
    )


# ---------------------------------------------------------------- příkazy

def cmd_login(_a) -> None:
    gc = import_lib()
    email = os.getenv("GARMIN_EMAIL") or input("Garmin e-mail: ")
    password = os.getenv("GARMIN_PASSWORD") or getpass("Garmin heslo: ")
    api = gc.Garmin(email, password, prompt_mfa=lambda: input("MFA kód: "))
    Path(TOKENSTORE).mkdir(parents=True, exist_ok=True)
    api.login(TOKENSTORE)
    print(f"Přihlášeno. Tokeny uloženy do {TOKENSTORE}")


def dig(d, *path):
    for p in path:
        if isinstance(d, list):
            d = d[0] if d else None
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)[:200]}


def cmd_wellness(a) -> None:
    api = connect()
    today = date.today()
    out = []
    for i in range(a.days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        sleep = safe(api.get_sleep_data, d)
        hrv = safe(api.get_hrv_data, d)
        summ = safe(api.get_user_summary, d)
        ready = safe(api.get_training_readiness, d)
        day = {
            "datum": d,
            "spanek_h": round((dig(sleep, "dailySleepDTO", "sleepTimeSeconds") or 0) / 3600, 1) or None,
            "spanek_skore": dig(sleep, "dailySleepDTO", "sleepScores", "overall", "value"),
            "hrv_noc_ms": dig(hrv, "hrvSummary", "lastNightAvg"),
            "hrv_7d_ms": dig(hrv, "hrvSummary", "weeklyAvg"),
            "hrv_status": dig(hrv, "hrvSummary", "status"),
            "hrv_baseline": [dig(hrv, "hrvSummary", "baseline", "balancedLow"),
                             dig(hrv, "hrvSummary", "baseline", "balancedUpper")],
            "klidovy_tep": dig(summ, "restingHeartRate"),
            "klidovy_tep_7d": dig(summ, "lastSevenDaysAvgRestingHeartRate"),
            "stres_prumer": dig(summ, "averageStressLevel"),
            "body_battery_rano": dig(summ, "bodyBatteryAtWakeTime"),
            "body_battery_max_min": [dig(summ, "bodyBatteryHighestValue"), dig(summ, "bodyBatteryLowestValue")],
            "readiness_skore": dig(ready, "score"),
            "readiness_uroven": dig(ready, "level"),
            "readiness_feedback": dig(ready, "feedbackShort"),
            "doba_zotaveni_h": round((dig(ready, "recoveryTime") or 0) / 60) or None,
        }
        if a.raw:
            day["_raw"] = {"sleep": sleep, "hrv": hrv, "summary": summ, "readiness": ready}
        out.append(day)
    status = safe(api.get_training_status, today.isoformat())
    latest = dig(status, "mostRecentTrainingStatus", "latestTrainingStatusData")
    dev = next(iter(latest.values()), {}) if isinstance(latest, dict) and latest else {}
    result = {
        "dny": out,
        "trenink_status": dig(dev, "trainingStatusFeedbackPhrase") or dig(dev, "trainingStatus"),
        "akutni_zatez_acwr": dig(dev, "acuteTrainingLoadDTO", "acwrPercent"),
        "acwr_status": dig(dev, "acuteTrainingLoadDTO", "acwrStatus"),
        "vo2max": dig(status, "mostRecentVO2Max", "generic", "vo2MaxValue"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=1, default=str))


def load_plan(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("workouts", [data])
    return data


def cmd_upload(a) -> None:
    import_lib()
    plan = load_plan(a.file)
    built = []
    for w in plan:
        try:
            datetime.strptime(w["date"], "%Y-%m-%d")
            built.append((w, build_workout(w)))
        except Exception as e:  # noqa: BLE001
            die(f"{w.get('date')} {w.get('name')}: {e}")
    if a.dry_run:
        for w, wo in built:
            print(f"OK  {w['date']}  {wo.workoutName}  (~{wo.estimatedDurationInSecs // 60} min)")
        if a.verbose:
            print(json.dumps([wo.to_dict() for _, wo in built], ensure_ascii=False, indent=1))
        print(f"\nValidace v pořádku: {len(built)} tréninků (nic nenahráno).")
        return

    api = connect()
    existing = scheduled_items(api, min(w["date"] for w, _ in built), max(w["date"] for w, _ in built))
    have = {(i["date"], i["title"]) for i in existing}
    log = []
    for w, wo in built:
        if (w["date"], wo.workoutName) in have:
            print(f"--  {w['date']}  {wo.workoutName}  už v kalendáři je, přeskakuji")
            continue
        res = api.upload_workout(wo.to_dict())
        wid = res.get("workoutId")
        api.schedule_workout(wid, w["date"])
        log.append({"date": w["date"], "name": wo.workoutName, "workoutId": wid})
        print(f"OK  {w['date']}  {wo.workoutName}  (id {wid})")
    print(json.dumps({"nahrano": log}, ensure_ascii=False))


def scheduled_items(api, d_from: str, d_to: str) -> list[dict]:
    start = datetime.strptime(d_from, "%Y-%m-%d").date().replace(day=1)
    end = datetime.strptime(d_to, "%Y-%m-%d").date()
    items, cur, seen = [], start, set()
    while cur <= end:
        data = api.get_scheduled_workouts(cur.year, cur.month) or {}
        for it in data.get("calendarItems") or []:
            # měsíční pohled obsahuje i přesahující týdny sousedních měsíců – bez duplicit
            if it.get("id") in seen:
                continue
            seen.add(it.get("id"))
            if it.get("itemType") == "workout" and d_from <= (it.get("date") or "") <= d_to:
                items.append({"date": it["date"], "title": it.get("title"), "scheduleId": it.get("id"),
                              "workoutId": it.get("workoutId"), "sport": it.get("sportTypeKey")})
        cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    return sorted(items, key=lambda x: x["date"])


def cmd_scheduled(a) -> None:
    api = connect()
    for it in scheduled_items(api, a.d_from, a.d_to):
        mark = "*" if (it["title"] or "").startswith(PREFIX) else " "
        print(f"{mark} {it['date']}  {it['title']}  (sport {it['sport']}, schedule {it['scheduleId']})")
    print("\n* = vytvořeno skillem trenér")


def cmd_remove(a) -> None:
    api = connect()
    mine = [i for i in scheduled_items(api, a.d_from, a.d_to) if (i["title"] or "").startswith(PREFIX)]
    for it in mine:
        print(f"{'(dry) ' if a.dry_run else ''}mažu {it['date']}  {it['title']}")
        if not a.dry_run:
            api.unschedule_workout(it["scheduleId"])
            if it.get("workoutId"):
                safe(api.delete_workout, it["workoutId"])
    print(f"Celkem {len(mine)} tréninků skillu.")


def cmd_zones(_a) -> None:
    api = connect()
    out = {"tepove_zony": [], "anp": None}
    for z in safe(api.get_heart_rate_zones) or []:
        fl = [z.get(f"zone{i}Floor") for i in range(1, 6)]
        mx = z.get("maxHeartRateUsed")
        out["tepove_zony"].append({
            "sport": z.get("sport"), "metoda": z.get("trainingMethod"),
            "max_tep": mx, "klidovy_tep": z.get("restingHeartRateUsed"),
            "anp_tep": z.get("lactateThresholdHeartRateUsed"),
            "zony": [[fl[i], (fl[i + 1] - 1) if i < 4 else mx] for i in range(5)],
        })
    lt = dig(safe(api.get_lactate_threshold) or {}, "speed_and_heart_rate") or {}
    if lt.get("heartRate"):
        # Garmin ukládá rychlost na ANP v desetinách m/s
        sp = (lt.get("speed") or 0) * 10
        pace = f"{int(1000 / sp // 60)}:{int(1000 / sp % 60):02d}" if sp else None
        out["anp"] = {"tep": lt["heartRate"], "tempo_min_km": pace, "datum": (lt.get("calendarDate") or "")[:10]}
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_exercise(a) -> None:
    import_lib()
    from garminconnect import exercises
    hits = exercises.find(" ".join(a.term))
    for e in hits[:40]:
        print(f"{e['name']:<50} {e['category']}/{e['exercise']}")
    if not hits:
        print("Nic nenalezeno – zkus anglický výraz (squat, lunge, plank, calf, hip raise...).")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Garmin Connect pro běžeckého trenéra")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login").set_defaults(fn=cmd_login)
    w = sub.add_parser("wellness")
    w.add_argument("--days", type=int, default=7)
    w.add_argument("--raw", action="store_true")
    w.set_defaults(fn=cmd_wellness)
    u = sub.add_parser("upload")
    u.add_argument("file")
    u.add_argument("--dry-run", action="store_true")
    u.add_argument("--verbose", action="store_true")
    u.set_defaults(fn=cmd_upload)
    for name, fn in (("scheduled", cmd_scheduled), ("remove", cmd_remove)):
        s = sub.add_parser(name)
        s.add_argument("--from", dest="d_from", required=True)
        s.add_argument("--to", dest="d_to", required=True)
        if name == "remove":
            s.add_argument("--dry-run", action="store_true")
        s.set_defaults(fn=fn)
    sub.add_parser("zones").set_defaults(fn=cmd_zones)
    e = sub.add_parser("exercise")
    e.add_argument("term", nargs="+")
    e.set_defaults(fn=cmd_exercise)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
