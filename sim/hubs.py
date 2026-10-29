"""Pick K resilience-hub / mobile-battery sites that cover the most weighted
danger within a travel radius (greedy max-coverage, a (1 - 1/e) approximation).
Homes are SYNTHETIC (sim/seed_homes.py); output is labeled simulated.

  python sim/hubs.py --homes 2000 --med-share X --elderly-share Y --k 5 --radius-km 2
  python sim/hubs.py ... --judge     # Nemotron Ultra writes the trade-offs (1 call)
"""
from __future__ import annotations
import argparse, json, math, os, pathlib, random, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from seed_homes import add_share_args, resolve_shares, seed  # noqa: E402


def danger_weight(h: dict) -> float:
    """Same factors as outage_sim.hours_in_danger: people, medical, age, heating speed."""
    return h["occupants"] * (2.0 if h["medical_load"] else 1.0) * (1.5 if h["elderly"] else 1.0) * h["hi_rise"]


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def candidates(homes: list[dict], n: int, rng: random.Random) -> list[tuple[float, float]]:
    """Candidate sites: a sample of home locations (stand-ins for schools, churches, fire stations)."""
    return [(h["lat"], h["lon"]) for h in rng.sample(homes, min(n, len(homes)))]


def greedy(homes: list[dict], sites: list[tuple[float, float]], k: int, radius_km: float) -> list[dict]:
    w = [danger_weight(h) for h in homes]
    cover = [{i for i, h in enumerate(homes) if km(s, (h["lat"], h["lon"])) <= radius_km} for s in sites]
    covered: set[int] = set()
    picks = []
    for _ in range(k):
        gains = [sum(w[i] for i in c - covered) for c in cover]
        j = max(range(len(sites)), key=gains.__getitem__)
        if gains[j] <= 0:
            break
        new = cover[j] - covered
        covered |= new
        picks.append({"lat": round(sites[j][0], 4), "lon": round(sites[j][1], 4),
                      "new_homes": len(new), "new_weight": round(gains[j], 1),
                      "medical_homes": sum(homes[i]["medical_load"] for i in new)})
    total = sum(w)
    for p in picks:
        p["share_of_danger"] = round(p["new_weight"] / total, 3)
    return picks


async def judge(picks: list[dict]) -> str:
    """One Nemotron Ultra call: plain-language trade-offs. It does not change the picks."""
    from openai import AsyncOpenAI
    c = AsyncOpenAI(base_url=os.environ.get("TOKEN_FACTORY_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
                    api_key=os.environ["NEBIUS_API_KEY"])
    r = await c.chat.completions.create(
        model=os.environ.get("NEMOTRON_ULTRA_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b"),
        max_tokens=500, temperature=0.2,
        messages=[{"role": "system", "content":
                   "You advise an emergency manager. Hub sites were chosen by a greedy coverage "
                   "algorithm on SIMULATED homes. Do not reorder them. In under 150 words, explain "
                   "the trade-offs between the sites, quoting the numbers given."},
                  {"role": "user", "content": json.dumps(picks)}])
    return r.choices[0].message.content or ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--homes", type=int, default=2000)
    add_share_args(ap)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--radius-km", type=float, default=2.0)
    ap.add_argument("--candidates", type=int, default=150)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--judge", action="store_true", help="1 Nemotron Ultra call for trade-offs")
    ap.add_argument("--out", default="data/processed/hubs.json")
    a = ap.parse_args()
    resolve_shares(a)
    rng = random.Random(a.seed)
    homes = seed(a.homes, a.med_share, a.elderly_share, max(4, a.homes // 50), rng=rng)
    picks = greedy(homes, candidates(homes, a.candidates, rng), a.k, a.radius_km)
    out = {"simulated": True, "params": vars(a), "hubs": picks,
           "covered_share": round(sum(p["share_of_danger"] for p in picks), 3)}
    if a.judge:
        import asyncio
        out["ultra_tradeoffs"] = asyncio.run(judge(picks))
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "params"}, indent=2))


if __name__ == "__main__":
    main()
