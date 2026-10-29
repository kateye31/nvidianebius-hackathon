"""Compare restoration orderings by person-hours spent above NWS 'danger' heat index.
Runs locally or as a Nebius Serverless Job. Output is labeled simulated.

Example:
  python sim/outage_sim.py --homes 2000 --zip 33956
  python sim/outage_sim.py --homes 2000 --med-share <emPOWER ratio> --elderly-share <ACS ratio>
"""
from __future__ import annotations
import argparse, json, pathlib, random, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from seed_homes import add_share_args, resolve_shares, seed  # noqa: E402

DANGER = 103.0


def hours_in_danger(h: dict, restored_at: float) -> float:
    if h["hi_start"] >= DANGER:
        t_cross = 0.0
    else:
        t_cross = (DANGER - h["hi_start"]) / h["hi_rise"]
    weight = h["occupants"] * (2.0 if h["medical_load"] else 1.0) * (1.5 if h["elderly"] else 1.0)
    return max(0.0, restored_at - t_cross) * weight


def run(homes: list[dict], crews: int, hours_per_feeder: float, order: str) -> float:
    feeders: dict[int, list[dict]] = {}
    for h in homes:
        feeders.setdefault(h["feeder"], []).append(h)
    if order == "biggest_first":
        seq = sorted(feeders, key=lambda f: len(feeders[f]), reverse=True)
    elif order == "nightlight":
        # danger avoided per crew-hour: favour feeders with many high-weight, fast-heating homes
        def urgency(f):
            return sum(h["occupants"] * (2 if h["medical_load"] else 1) * h["hi_rise"] for h in feeders[f])
        seq = sorted(feeders, key=urgency, reverse=True)
    else:
        raise ValueError(order)
    crew_free = [0.0] * crews
    total = 0.0
    for f in seq:
        i = min(range(crews), key=crew_free.__getitem__)
        crew_free[i] += hours_per_feeder
        total += sum(hours_in_danger(h, crew_free[i]) for h in feeders[f])
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--homes", type=int, default=2000)
    ap.add_argument("--feeders", type=int, default=40)
    ap.add_argument("--crews", type=int, default=4)
    ap.add_argument("--hours-per-feeder", type=float, default=6.0)
    add_share_args(ap)
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--out", default="data/processed/sim_result.json")
    a = ap.parse_args()
    resolve_shares(a)

    res = {"biggest_first": [], "nightlight": []}
    for t in range(a.trials):
        homes = seed(a.homes, a.med_share, a.elderly_share, a.feeders, rng=random.Random(t))
        for k in res:
            res[k].append(run(homes, a.crews, a.hours_per_feeder, k))
    summary = {k: sum(v) / len(v) for k, v in res.items()}
    summary["reduction_pct"] = round(100 * (1 - summary["nightlight"] / summary["biggest_first"]), 1)
    out = {"simulated": True, "params": vars(a), "mean_weighted_person_hours": summary, "trials": res}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
