"""Výpočet VDOT a tréninkových temp z času závodu (vzorce J. Danielse / Gilberta).

Použití:
    python tempa.py <vzdálenost> <čas>
    python tempa.py 10k 42:30
    python tempa.py pulmaraton 1:35:10
    python tempa.py 7.5 31:20        # vzdálenost v km

Vypíše VDOT, predikce závodních časů a tréninková tempa (min/km).
"""
import math
import sys

DISTANCES = {
    "1500": 1.5, "1500m": 1.5, "mile": 1.609344, "mile1": 1.609344,
    "3k": 3.0, "3000": 3.0, "5k": 5.0, "5km": 5.0, "10k": 10.0, "10km": 10.0,
    "15k": 15.0, "pulmaraton": 21.0975, "pm": 21.0975, "hm": 21.0975, "half": 21.0975,
    "maraton": 42.195, "m": 42.195, "marathon": 42.195,
}


def parse_time(s: str) -> float:
    """Vrátí čas v minutách z formátu h:mm:ss nebo mm:ss."""
    parts = [float(p) for p in s.split(":")]
    if len(parts) == 3:
        h, m, sec = parts
    elif len(parts) == 2:
        h, m, sec = 0, *parts
    else:
        raise ValueError(f"Neplatný čas: {s}")
    return h * 60 + m + sec / 60


def vo2_at(v: float) -> float:
    """Spotřeba kyslíku (ml/kg/min) při rychlosti v (m/min)."""
    return -4.60 + 0.182258 * v + 0.000104 * v * v


def pct_max(t: float) -> float:
    """Podíl VO2max udržitelný po dobu t minut."""
    return 0.8 + 0.1894393 * math.exp(-0.012778 * t) + 0.2989558 * math.exp(-0.1932605 * t)


def vdot(dist_km: float, t_min: float) -> float:
    v = dist_km * 1000 / t_min
    return vo2_at(v) / pct_max(t_min)


def velocity_for_vo2(vo2: float) -> float:
    """Inverze vo2_at: rychlost (m/min) pro danou spotřebu O2."""
    a, b, c = 0.000104, 0.182258, -4.60 - vo2
    return (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)


def predict_time(vd: float, dist_km: float) -> float:
    """Predikce času (min) na trať pro dané VDOT – bisekce."""
    lo, hi = 1.0, 600.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if vdot(dist_km, mid) > vd:
            lo = mid  # příliš rychle -> delší čas
        else:
            hi = mid
    return (lo + hi) / 2


def pace(v_m_min: float) -> str:
    sec = int(round(1000 / v_m_min * 60))
    return f"{sec // 60}:{sec % 60:02d}"


def fmt_time(t_min: float) -> str:
    total = int(round(t_min * 60))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    key = sys.argv[1].lower()
    dist = DISTANCES.get(key) or float(key.replace(",", "."))
    t = parse_time(sys.argv[2])
    vd = vdot(dist, t)

    print(f"Závod: {dist:g} km za {fmt_time(t)}  ->  VDOT {vd:.1f}\n")
    print("Predikce závodů (rovnocenný výkon):")
    for name, d in [("1500 m", 1.5), ("5 km", 5.0), ("10 km", 10.0),
                    ("Půlmaraton", 21.0975), ("Maraton", 42.195)]:
        pt = predict_time(vd, d)
        print(f"  {name:<11} {fmt_time(pt):>8}  ({pace(d * 1000 / pt)}/km)")

    m_pace = 42195 / predict_time(vd, 42.195)
    e_slow, e_fast = velocity_for_vo2(vd * 0.62), velocity_for_vo2(vd * 0.74)
    t_v = velocity_for_vo2(vd * 0.88)
    i_v = velocity_for_vo2(vd * 0.975)
    r_v = 1609.344 / predict_time(vd, 1.609344)

    print("\nTréninková tempa (min/km):")
    print(f"  E  – lehký / dlouhý běh   {pace(e_fast)} – {pace(e_slow)}")
    print(f"  M  – maratonské tempo     {pace(m_pace)}")
    print(f"  T  – prahové tempo        {pace(t_v)}   (400 m: {fmt_time(400 / t_v)})")
    print(f"  I  – intervaly (VO2max)   {pace(i_v)}   (400 m: {fmt_time(400 / i_v)})")
    print(f"  R  – opakování (rychlost) {pace(r_v)}   (200 m: {fmt_time(200 / r_v)}, 400 m: {fmt_time(400 / r_v)})")


if __name__ == "__main__":
    main()
