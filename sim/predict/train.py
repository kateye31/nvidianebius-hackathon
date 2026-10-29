"""County outage forecaster on REAL data, tested on a held-out storm (Milton 2024).

Train: EAGLE-I Florida county outages for Irma 2017, Michael 2018, Ian 2022,
       Idalia 2023, Helene 2024. Test: Milton 2024 (never seen in training).
Features per county x storm (from HURDAT2 + Census gazetteer + EAGLE-I MCC):
  closest distance to the track, wind at closest approach, max wind within
  100 km, forward speed at closest approach, log customers, land area.
Targets: peak % customers out; hours from peak to 50% restored (counties
  with >= 5% out; censored at the window end if never reached, flagged).
Model: sklearn HistGradientBoostingRegressor, small. Baseline: training mean.

  python data/fetch_storms.py && python data/fetch_eaglei.py   # first
  python sim/predict/train.py
"""
from __future__ import annotations
import csv, datetime as dt, json, math, pathlib, sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
from fetch_storms import STORMS, TEST_STORM, load_tracks  # noqa: E402

RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
FEATURES = ["dist_km", "wind_at_closest_kt", "max_wind_100km_kt", "fwd_speed_kmh", "log_customers", "land_sqmi"]


def km(a_lat, a_lon, b_lat, b_lon) -> float:
    p = math.radians
    h = math.sin(p(b_lat - a_lat) / 2) ** 2 + math.cos(p(a_lat)) * math.cos(p(b_lat)) * math.sin(p(b_lon - a_lon) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def hourly(track: list[dict]) -> list[dict]:
    """Linear interpolation of the 6-hourly best track to 1-hour steps."""
    out = []
    for a, b in zip(track, track[1:]):
        n = max(1, int((b["t"] - a["t"]).total_seconds() // 3600))
        for i in range(n):
            f = i / n
            out.append({k: a[k] + (b[k] - a[k]) * f for k in ("lat", "lon", "wind_kt")} | {"t": a["t"] + dt.timedelta(hours=i)})
    return out + track[-1:]


def storm_features(track: list[dict], c: dict) -> dict:
    pts = hourly(track)
    d = [km(c["lat"], c["lon"], p["lat"], p["lon"]) for p in pts]
    i = min(range(len(pts)), key=d.__getitem__)
    j = min(i + 1, len(pts) - 1); k = max(i - 1, 0)
    hrs = max(1e-6, (pts[j]["t"] - pts[k]["t"]).total_seconds() / 3600)
    return {"dist_km": d[i], "wind_at_closest_kt": pts[i]["wind_kt"],
            "max_wind_100km_kt": max([p["wind_kt"] for p, x in zip(pts, d) if x <= 100], default=0),
            "fwd_speed_kmh": km(pts[k]["lat"], pts[k]["lon"], pts[j]["lat"], pts[j]["lon"]) / hrs}


def outage_targets(path: pathlib.Path, mcc: dict[str, int], end: str) -> dict[str, dict]:
    series: dict[str, list[tuple[dt.datetime, int]]] = defaultdict(list)
    for r in csv.DictReader(path.open()):
        out_ = r.get("customers_out", r.get("sum"))   # the 2023 file names the column "sum"
        series[r["fips_code"].zfill(5)].append((dt.datetime.fromisoformat(r["run_start_time"]), int(float(out_ or 0))))
    end_t = dt.datetime.fromisoformat(end + " 23:59:59")
    out = {}
    for fips, s in series.items():
        s.sort()
        t_peak, peak = max(s, key=lambda x: x[1])
        cust = mcc.get(fips)
        if not cust or peak <= 0:
            continue
        after = [t for t, v in s if t > t_peak and v <= peak / 2]
        out[fips] = {"peak_pct_out": min(100.0, 100 * peak / cust),
                     "hours_to_50": ((after[0] if after else end_t) - t_peak).total_seconds() / 3600,
                     "censored": not after}
    return out


def build() -> list[dict]:
    mcc = {}
    for r in csv.DictReader((RAW / "eaglei_mcc.csv").open(encoding="utf-8-sig")):
        mcc[r["County_FIPS"].zfill(5)] = int(r["Customers"])
    counties = [{"fips": r["fips"], "name": r["name"], "lat": float(r["lat"]), "lon": float(r["lon"]),
                 "land_sqmi": float(r["aland_sqmi"])} for r in csv.DictReader((RAW / "fl_counties.csv").open())]
    tracks = load_tracks(RAW / "hurdat2.txt", set(STORMS))
    rows = []
    for sid, (name, _start, end) in STORMS.items():
        tg = outage_targets(RAW / f"eaglei_fl_{name.lower()}.csv", mcc, end)
        for c in counties:
            if c["fips"] not in mcc:
                continue
            t = tg.get(c["fips"], {"peak_pct_out": 0.0, "hours_to_50": None, "censored": False})
            rows.append({"storm": sid, "storm_name": name, "fips": c["fips"], "county": c["name"],
                         **storm_features(tracks[sid], c), "log_customers": math.log10(mcc[c["fips"]]),
                         "land_sqmi": c["land_sqmi"], **t})
    return rows


def fit_eval(train: list[dict], test: list[dict], target: str) -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor
    X = lambda rs: [[r[f] for f in FEATURES] for r in rs]  # noqa: E731
    m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=3,
                                      min_samples_leaf=10, random_state=0)
    m.fit(X(train), [r[target] for r in train])
    pred = m.predict(X(test))
    mean = sum(r[target] for r in train) / len(train)
    mae = sum(abs(p - r[target]) for p, r in zip(pred, test)) / len(test)
    base = sum(abs(mean - r[target]) for r in test) / len(test)
    return {"mae": round(mae, 2), "baseline_mae_train_mean": round(base, 2), "n_train": len(train),
            "n_test": len(test), "pred": [round(float(p), 1) for p in pred]}


def main() -> None:
    rows = build()
    train = [r for r in rows if r["storm"] != TEST_STORM]
    test = [r for r in rows if r["storm"] == TEST_STORM]
    peak = fit_eval(train, test, "peak_pct_out")
    hit = lambda rs: [r for r in rs if r["hours_to_50"] is not None and r["peak_pct_out"] >= 5]  # noqa: E731
    rest = fit_eval(hit(train), hit(test), "hours_to_50")
    by_fips = {r["fips"]: p for r, p in zip(hit(test), rest["pred"])}
    out = {
        "simulated": False, "source": "EAGLE-I (ORNL) + NOAA HURDAT2 + Census gazetteer; real data",
        "train_storms": [STORMS[s][0] for s in STORMS if s != TEST_STORM], "test_storm": STORMS[TEST_STORM][0],
        "features": FEATURES,
        "mae_peak_pct_out": peak["mae"], "baseline_mae_peak_pct_out": peak["baseline_mae_train_mean"],
        "mae_hours_to_50": rest["mae"], "baseline_mae_hours_to_50": rest["baseline_mae_train_mean"],
        "n_train": peak["n_train"], "n_test": peak["n_test"],
        "censored_test_counties": sum(r["censored"] for r in hit(test)),
        "milton_counties": [{"fips": r["fips"], "county": r["county"],
                             "actual_peak_pct_out": round(r["peak_pct_out"], 1), "pred_peak_pct_out": p,
                             "actual_hours_to_50": None if r["hours_to_50"] is None else round(r["hours_to_50"], 1),
                             "pred_hours_to_50": by_fips.get(r["fips"])}
                            for r, p in sorted(zip(test, peak["pred"]), key=lambda x: -x[0]["peak_pct_out"])],
    }
    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "predict_milton.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "milton_counties"}, indent=2))
    print("top Milton counties:", json.dumps(out["milton_counties"][:5], indent=1))


if __name__ == "__main__":
    main()
