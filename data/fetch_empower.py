"""Real ZIP-level ratios for seeding synthetic homes -> data/processed/zip_ratios.csv

- HHS emPOWER REST service (layer 1, "Electricity Dependent DME – ALL – ZipLevel"):
  Medicare beneficiaries with electricity-dependent equipment, per Florida ZIP.
- Census ACS 5-year 2023 (needs a free key in CENSUS_API_KEY,
  https://api.census.gov/data/key_signup.html): households (B11001_001E) and
  households with someone 65+ (B11007_002E), per ZCTA.

med_share = emPOWER DME users / households (approximation: about one DME user
per household). elderly_share = households with 65+ / households.

  python data/fetch_empower.py
"""
from __future__ import annotations
import csv, json, os, pathlib, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RAW, PROC = HERE / "raw", HERE / "processed"
EMPOWER = ("https://services2.arcgis.com/ZQ4jTQn6k7VPXEwO/arcgis/rest/services/"
           "HHS_emPOWER_REST_Service_Public/FeatureServer/1/query")
ACS = "https://api.census.gov/data/2023/acs/acs5"


def empower_fl() -> list[dict]:
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"where": "STATE='FL'", "returnGeometry": "false", "f": "json",
                                    "outFields": "Zip_Code,COUNTY,FIPS_Code,Medicare_Benes,Power_Dependent_Devices_DME",
                                    "resultOffset": offset, "resultRecordCount": 1000})
        d = json.load(urllib.request.urlopen(f"{EMPOWER}?{q}", timeout=60))
        feats = [f["attributes"] for f in d.get("features", [])]
        rows += feats
        if not d.get("exceededTransferLimit") or not feats:
            return rows
        offset += len(feats)


def acs_zcta(key: str) -> dict[str, tuple[int, int]]:
    q = urllib.parse.urlencode({"get": "B11001_001E,B11007_002E", "for": "zip code tabulation area:*", "key": key})
    data = json.load(urllib.request.urlopen(f"{ACS}?{q}", timeout=120))
    return {r[2]: (int(r[0]), int(r[1])) for r in data[1:] if r[0] and r[1]}


def main() -> None:
    RAW.mkdir(exist_ok=True); PROC.mkdir(exist_ok=True)
    emp = empower_fl()
    with open(RAW / "empower_fl_zip.csv", "w", newline="") as w:
        wr = csv.DictWriter(w, fieldnames=list(emp[0]))
        wr.writeheader(); wr.writerows(emp)
    print(f"emPOWER: {len(emp)} Florida ZIPs -> raw/empower_fl_zip.csv")
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("CENSUS_API_KEY not set: skipped ACS, so no zip_ratios.csv yet. "
              "Get a free key at https://api.census.gov/data/key_signup.html")
        return
    acs = acs_zcta(key)
    n = 0
    with open(PROC / "zip_ratios.csv", "w", newline="") as w:
        wr = csv.writer(w)
        wr.writerow(["zip", "county", "households", "dme_users", "med_share", "elderly_share"])
        for e in emp:
            hh, old = acs.get(str(e["Zip_Code"]).zfill(5), (0, 0))
            if hh < 50:                 # too few households for a stable ratio
                continue
            dme = e["Power_Dependent_Devices_DME"] or 0
            wr.writerow([str(e["Zip_Code"]).zfill(5), e["COUNTY"], hh, dme,
                         round(min(1.0, dme / hh), 4), round(old / hh, 4)])
            n += 1
    print(f"{n} ZIPs -> processed/zip_ratios.csv (log sources in data/SOURCES.lock.md)")


if __name__ == "__main__":
    main()
