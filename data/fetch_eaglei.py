"""EAGLE-I county outages (ORNL), Florida only, for the storms in fetch_storms.STORMS.

Source: figshare article 24237376 (DOI 10.6084/m9.figshare.24237376), one CSV
per year (~1 GB each). We stream each year and keep only Florida rows inside a
storm window, so the full national files never touch the disk.
Also fetches MCC.csv (modeled customers per county) and the Census county
gazetteer (county centroids) used as model features.

  python data/fetch_eaglei.py            # ~5.5 GB streamed, a few minutes per year
"""
from __future__ import annotations
import csv, io, json, pathlib, sys, time, urllib.request, zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fetch_storms import STORMS  # noqa: E402

RAW = pathlib.Path(__file__).resolve().parent / "raw"
ARTICLE = "https://api.figshare.com/v2/articles/24237376"
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip"


def files() -> dict[str, str]:
    meta = json.load(urllib.request.urlopen(ARTICLE, timeout=60))
    return {f["name"]: f["download_url"] for f in meta["files"]}


def stream_lines(url: str, retries: int = 8):
    """Yield decoded lines; on a dropped connection, resume with an HTTP Range
    request from the end of the last complete line (figshare resets ~1 GB reads)."""
    offset, attempt = 0, 0
    while True:
        req = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                if offset and r.status != 206:
                    raise RuntimeError("server ignored Range; cannot resume")
                buf = b""
                while chunk := r.read(1 << 20):
                    buf += chunk
                    *lines, buf = buf.split(b"\n")
                    for ln in lines:
                        offset += len(ln) + 1
                        yield ln.decode("utf-8-sig" if offset == len(ln) + 1 else "utf-8")
                if buf:
                    yield buf.decode()
                return
        except (ConnectionError, TimeoutError, OSError) as e:
            attempt += 1
            if attempt > retries:
                raise
            print(f"  connection dropped at {offset / 1e9:.2f} GB ({type(e).__name__}); resuming")
            time.sleep(min(30, 2 ** attempt))


def storm_slice(url: str, sid: str, name: str, start: str, end: str) -> pathlib.Path:
    out = RAW / f"eaglei_fl_{name.lower()}.csv"
    if out.exists():
        print(f"{out.name} exists, skipping")
        return out
    kept = 0
    with open(out.with_suffix(".part"), "w", newline="") as w:
        rows = csv.reader(stream_lines(url))
        header = next(rows)
        i_state, i_time = header.index("state"), header.index("run_start_time")
        wr = csv.writer(w)
        wr.writerow(header)
        end_day = end + " 23:59:59"
        for row in rows:
            if row[i_state] == "Florida" and start <= row[i_time] <= end_day:
                wr.writerow(row)
                kept += 1
    out.with_suffix(".part").rename(out)
    print(f"{sid} {name}: {kept} Florida rows -> {out.name}")
    return out


def main() -> None:
    RAW.mkdir(exist_ok=True)
    f = files()
    urllib.request.urlretrieve(f["MCC.csv"], RAW / "eaglei_mcc.csv")
    with zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(GAZ, timeout=120).read())) as z:
        lines = z.read(z.namelist()[0]).decode("latin-1").splitlines()
    rows = [[c.strip() for c in ln.split("\t")] for ln in lines]
    hdr = rows[0]
    with open(RAW / "fl_counties.csv", "w", newline="") as w:
        wr = csv.writer(w)
        wr.writerow(["fips", "name", "lat", "lon", "aland_sqmi"])
        for r in rows[1:]:
            if r[hdr.index("USPS")] == "FL":
                wr.writerow([r[hdr.index("GEOID")], r[hdr.index("NAME")], r[hdr.index("INTPTLAT")],
                             r[hdr.index("INTPTLONG")], r[hdr.index("ALAND_SQMI")]])
    for sid, (name, start, end) in STORMS.items():
        storm_slice(f[f"eaglei_outages_{start[:4]}.csv"], sid, name, start, end)
    print("log the files in data/SOURCES.lock.md")


if __name__ == "__main__":
    main()
