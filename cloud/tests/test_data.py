import sys, pathlib, argparse
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "data"), str(ROOT / "sim"), str(ROOT / "sim" / "predict")]
import pytest
from fetch_storms import load_tracks
import train, seed_homes

HURDAT = """AL142024,             MILTON,      3,
20241009, 1800,  , HU, 27.0N,  83.0W, 100,  950,
20241010, 0000,  , HU, 27.3N,  82.3W,  90,  955,
20241010, 0600,  , HU, 27.8N,  81.3W,  70,  975,
AL092024,             HELENE,      1,
20240926, 1800,  , HU, 28.0N,  84.0W, 120,  938,
"""


def test_hurdat_parse_signs_and_filter(tmp_path):
    p = tmp_path / "h.txt"; p.write_text(HURDAT)
    tr = load_tracks(p, {"AL142024"})
    assert list(tr) == ["AL142024"] and len(tr["AL142024"]) == 3
    assert tr["AL142024"][0]["lon"] == -83.0 and tr["AL142024"][0]["wind_kt"] == 100


def test_storm_features_closest_point(tmp_path):
    p = tmp_path / "h.txt"; p.write_text(HURDAT)
    track = load_tracks(p, {"AL142024"})["AL142024"]
    f = train.storm_features(track, {"lat": 27.3, "lon": -82.3})
    assert f["dist_km"] < 5 and f["wind_at_closest_kt"] == pytest.approx(90, abs=2)
    assert f["max_wind_100km_kt"] >= 90 and 10 < f["fwd_speed_kmh"] < 40


def test_outage_targets_peak_and_half_restore(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("fips_code,county,state,customers_out,run_start_time\n"
                 "12071,Lee,Florida,100,2024-10-09 00:00:00\n"
                 "12071,Lee,Florida,800,2024-10-10 00:00:00\n"
                 "12071,Lee,Florida,500,2024-10-11 00:00:00\n"
                 "12071,Lee,Florida,300,2024-10-12 00:00:00\n"
                 "12099,X,Florida,50,2024-10-10 00:00:00\n")
    t = train.outage_targets(p, {"12071": 1000, "12099": 100}, "2024-10-20")
    assert t["12071"]["peak_pct_out"] == 80 and t["12071"]["hours_to_50"] == 48 and not t["12071"]["censored"]
    assert t["12099"]["censored"]


def test_zip_shares_from_processed_file(tmp_path, monkeypatch):
    f = tmp_path / "zip_ratios.csv"
    f.write_text("zip,county,households,dme_users,med_share,elderly_share\n33956,Lee,2000,51,0.0255,0.61\n")
    monkeypatch.setattr(seed_homes, "RATIOS", f)
    assert seed_homes.resolve_shares(argparse.Namespace(zip="33956", med_share=None, elderly_share=None)) == (0.0255, 0.61)
    with pytest.raises(SystemExit):
        seed_homes.resolve_shares(argparse.Namespace(zip=None, med_share=None, elderly_share=None))
