"""NOAA HURDAT2 Atlantic best tracks -> data/raw/hurdat2.txt, plus a parser.

Source: https://www.nhc.noaa.gov/data/hurdat/ (newest hurdat2-1851-*.txt).
  python data/fetch_storms.py
"""
from __future__ import annotations
import datetime as dt, pathlib, re, sys, urllib.request

RAW = pathlib.Path(__file__).resolve().parent / "raw"
INDEX = "https://www.nhc.noaa.gov/data/hurdat/"

# Florida storms used for training; Milton is held out for the test.
# Window = days whose EAGLE-I outage records belong to the storm (UTC dates).
STORMS = {
    "AL112017": ("IRMA", "2017-09-08", "2017-09-25"),
    "AL142018": ("MICHAEL", "2018-10-08", "2018-10-25"),
    "AL092022": ("IAN", "2022-09-26", "2022-10-12"),
    "AL102023": ("IDALIA", "2023-08-28", "2023-09-10"),
    "AL092024": ("HELENE", "2024-09-24", "2024-10-07"),
    "AL142024": ("MILTON", "2024-10-08", "2024-10-22"),
}
TEST_STORM = "AL142024"


def fetch() -> pathlib.Path:
    html = urllib.request.urlopen(INDEX, timeout=60).read().decode()
    names = sorted(set(re.findall(r"hurdat2-1851-\d{4}-\d+\.txt", html)))
    if not names:
        sys.exit(f"no hurdat2-1851-*.txt listed at {INDEX}")
    # newest by the data year, then by release date suffix (MMDDYY or MMDDYYYY)
    def key(n: str):
        year, rel = re.match(r"hurdat2-1851-(\d{4})-(\d+)\.txt", n).groups()
        return int(year), rel[-2:], rel[:4]          # (data year, release yy, release mmdd)
    name = max(names, key=key)
    RAW.mkdir(exist_ok=True)
    out = RAW / "hurdat2.txt"
    urllib.request.urlretrieve(INDEX + name, out)
    print(f"{name} -> {out}  (log it in data/SOURCES.lock.md)")
    return out


def _coord(s: str) -> float:
    v = float(s[:-1])
    return -v if s[-1] in "SW" else v


def load_tracks(path: pathlib.Path, ids: set[str]) -> dict[str, list[dict]]:
    """{storm_id: [{t, lat, lon, wind_kt}, ...]} for the requested storms."""
    tracks: dict[str, list[dict]] = {}
    cur = None
    for line in path.read_text().splitlines():
        f = [x.strip() for x in line.split(",")]
        if re.fullmatch(r"AL\d{6}", f[0]):
            cur = f[0] if f[0] in ids else None
            if cur:
                tracks[cur] = []
        elif cur:
            t = dt.datetime.strptime(f[0] + f[1].zfill(4), "%Y%m%d%H%M")
            tracks[cur].append({"t": t, "lat": _coord(f[4]), "lon": _coord(f[5]), "wind_kt": int(f[6])})
    return tracks


if __name__ == "__main__":
    p = fetch()
    tr = load_tracks(p, set(STORMS))
    for sid, (name, *_ ) in STORMS.items():
        pts = tr.get(sid, [])
        print(f"{sid} {name}: {len(pts)} points, max {max((x['wind_kt'] for x in pts), default=0)} kt")
