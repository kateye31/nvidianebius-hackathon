"""Send packets to the API without hardware. Everything sent here is synthetic.

  python tools_send_test_packet.py                      # one test unit (9001)
  python tools_send_test_packet.py --fleet 150 --med-share X --elderly-share Y
      # SIMULATED homes around the island, seeded by sim/seed_homes.py.
      # X: emPOWER electricity-dependent share for the ZIP; Y: ACS 65+ share.
"""
import argparse, base64, os, sys, pathlib, random, httpx
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "sim"))
from app.packet import Packet, encode, F_GRID, F_MED, F_SOS, BATTERY_UNKNOWN
from app.heat import heat_index_f, tier, f_to_c

API = os.environ.get("API", "http://localhost:8000")
HDR = {"X-Unit-Key": os.environ.get("INGEST_KEY", "change-me")}


def post(c: httpx.Client, p: Packet, lat: float, lon: float) -> None:
    r = c.post(API + "/v1/ingest", headers=HDR, json={
        "p": base64.b64encode(encode(p)).decode(), "lat": lat, "lon": lon, "synthetic": True})
    r.raise_for_status()


def temp_for_hi(hi_f: float, rh: float) -> float:
    """Air temperature (F) that gives this heat index at this humidity (bisection)."""
    lo, hi = 50.0, 130.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if heat_index_f(mid, rh) < hi_f else (lo, mid)
    return lo


def fleet(n: int, med_share: float, elderly_share: float, seed: int) -> None:
    from seed_homes import seed as seed_homes
    rng = random.Random(seed)
    homes = seed_homes(n, med_share, elderly_share, n_feeders=max(4, n // 25), rng=rng)
    restored = set(rng.sample(range(n), n // 5))           # some feeders already back
    with httpx.Client(timeout=10) as c:
        for i, h in enumerate(homes):
            unit = 10000 + i                                  # u16 range; real units stay < 10000
            hours_dark = 0.0 if i in restored else rng.uniform(2, 18)
            still_min = rng.choice([0, 30, 90, 240, 600, 900])
            flags = (F_GRID if not hours_dark else 0) | (F_MED if h["medical_load"] else 0)
            flags |= F_SOS if rng.random() < 0.01 else 0
            for k in range(4):                                # 4 hourly readings -> forecast
                hrs = max(0.0, hours_dark - (3 - k))
                hi_f = min(118.0, h["hi_start"] + h["hi_rise"] * hrs) if hours_dark else h["hi_start"]
                rh = 65 + rng.uniform(-5, 5)
                p = Packet(1, unit, k, flags, BATTERY_UNKNOWN, round(f_to_c(temp_for_hi(hi_f, rh)), 1),
                           round(rh), round(f_to_c(hi_f), 1), min(tier(hi_f), 4), still_min,
                           round(hrs * 60), h["occupants"], 100000 + k * 3600)
                post(c, p, h["lat"], h["lon"])
    print(f"sent {n} SIMULATED homes ({len(restored)} restored) to {API}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fleet", type=int, default=0, help="number of simulated homes")
    ap.add_argument("--med-share", type=float, help="from emPOWER for the ZIP")
    ap.add_argument("--elderly-share", type=float, help="from Census ACS")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.fleet:
        if a.med_share is None or a.elderly_share is None:
            ap.error("--fleet needs --med-share and --elderly-share (real ratios, see docs/DATA.md)")
        fleet(a.fleet, a.med_share, a.elderly_share, a.seed)
        return
    p = Packet(1, 9001, 1, F_MED, 77, 32.0, 72, 40.5, 3, 200, 420, 2, 9999)
    with httpx.Client(timeout=10) as c:
        post(c, p, 26.6, -82.1)
    print("sent synthetic test unit 9001")


if __name__ == "__main__":
    main()
