"""Blue-sky days (HackSTEM priorities 2 and 3): during a heat-wave peak, cycle
enrolled AC in rotating groups to shave load. Medical homes are never cycled,
and a home drops out of the event once its indoor heat index rises more than
--cap-f above where it started. Everything here is SIMULATED and labeled.

Model assumptions (stated, not measured): outdoor temperature is a sine over
the afternoon; an idle home warms toward outdoors at a per-home rate; a
running AC draws --ac-kw and cools 3 F/h toward the setpoint.

  python sim/demand_response.py --homes 5000 --med-share X --elderly-share Y
"""
from __future__ import annotations
import argparse, json, math, pathlib, random, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from seed_homes import seed  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud"))
from app.heat import heat_index_f  # noqa: E402  same NWS formula as the scorer

DT_H = 5 / 60


def outdoor_f(hour: float, peak_f: float) -> float:
    return peak_f - 12 + 12 * max(0.0, math.sin(math.pi * (hour - 9) / 12))


def simulate(homes: list[dict], start_h: float, end_h: float, groups: int, cap_f: float,
             ac_kw: float, peak_f: float, rh: float, setpoint_f: float = 76.0) -> dict:
    enrolled = [h for h in homes if not h["medical_load"]]
    state = [{"t": setpoint_f, "out": False, "rate": 0.12 + 0.2 * (h["hi_rise"] - 0.8) / 1.4}
             for h in enrolled]
    hi0 = heat_index_f(setpoint_f, rh)
    shaved_kw, steps, max_rise, t = 0.0, 0, 0.0, start_h
    while t < end_h:
        active_group = int((t - start_h) / 0.25) % groups      # each group off 15 min in turn
        off_now = 0
        for i, s in enumerate(state):
            cycled = not s["out"] and i % groups == active_group
            if cycled:
                s["t"] += (outdoor_f(t, peak_f) - s["t"]) * s["rate"] * DT_H
                off_now += 1
            else:
                s["t"] = max(setpoint_f, s["t"] - 3 * DT_H)
            rise = heat_index_f(s["t"], rh) - hi0
            max_rise = max(max_rise, rise)
            if rise > cap_f:
                s["out"] = True                                 # comfort cap: opt this home out
        shaved_kw += off_now * ac_kw
        steps += 1
        t += DT_H
    return {
        "simulated": True,
        "enrolled_homes": len(enrolled),
        "medical_homes_never_cycled": len(homes) - len(enrolled),
        "avg_mw_shaved": round(shaved_kw / steps / 1000, 2),
        "max_indoor_hi_rise_f": round(max_rise, 1),
        "homes_opted_out_by_cap": sum(s["out"] for s in state),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--homes", type=int, default=5000)
    ap.add_argument("--med-share", type=float, required=True, help="from emPOWER for the ZIP")
    ap.add_argument("--elderly-share", type=float, required=True, help="from Census ACS")
    ap.add_argument("--start-h", type=float, default=14.0)
    ap.add_argument("--end-h", type=float, default=18.0)
    ap.add_argument("--groups", type=int, default=4, help="4 groups = each AC off 25%% of the time")
    ap.add_argument("--cap-f", type=float, default=4.0, help="max indoor heat-index rise per home")
    ap.add_argument("--ac-kw", type=float, default=3.0, help="assumed central AC draw")
    ap.add_argument("--peak-f", type=float, default=96.0)
    ap.add_argument("--rh", type=float, default=55.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="data/processed/demand_response.json")
    a = ap.parse_args()
    homes = seed(a.homes, a.med_share, a.elderly_share, 40, rng=random.Random(a.seed))
    res = simulate(homes, a.start_h, a.end_h, a.groups, a.cap_f, a.ac_kw, a.peak_f, a.rh)
    res["params"] = vars(a)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "params"}, indent=2))


if __name__ == "__main__":
    main()
