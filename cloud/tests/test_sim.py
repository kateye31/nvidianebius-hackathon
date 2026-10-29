import sys, pathlib, random
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sim"))
from seed_homes import seed
import hubs, demand_response, outage_sim


def homes(n=600, s=1):
    return seed(n, 0.05, 0.4, 12, rng=random.Random(s))


def test_all_seeded_homes_are_labeled_synthetic():
    assert all(h["synthetic"] for h in homes())


def test_hubs_greedy_beats_random_sites():
    h = homes()
    rng = random.Random(0)
    sites = hubs.candidates(h, 80, rng)
    picks = hubs.greedy(h, sites, 3, 2.0)
    rand = hubs.greedy(h, rng.sample(sites, 3), 3, 2.0)
    assert sum(p["new_weight"] for p in picks) >= sum(p["new_weight"] for p in rand)
    assert picks[0]["new_weight"] >= picks[-1]["new_weight"]   # diminishing gains


def test_demand_response_never_cycles_medical_and_respects_cap():
    h = homes()
    r = demand_response.simulate(h, 14, 18, groups=4, cap_f=4.0, ac_kw=3.0, peak_f=100, rh=60)
    assert r["medical_homes_never_cycled"] == sum(x["medical_load"] for x in h)
    assert r["enrolled_homes"] + r["medical_homes_never_cycled"] == len(h)
    assert r["avg_mw_shaved"] > 0
    # a home can overshoot the cap by at most one 5-minute step before opting out
    assert r["max_indoor_hi_rise_f"] < 4.0 + 1.0


def test_nightlight_order_beats_biggest_feeder_first_on_average():
    tot = {"biggest_first": 0.0, "nightlight": 0.0}
    for s in range(10):
        h = homes(400, s)
        for k in tot:
            tot[k] += outage_sim.run(h, crews=3, hours_per_feeder=6, order=k)
    assert tot["nightlight"] < tot["biggest_first"]
