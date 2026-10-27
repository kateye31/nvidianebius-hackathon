# Data

Raw downloads go in `data/raw/` (gitignored). Processed tables go in
`data/processed/`. Log every file you download in `SOURCES.lock.md`
(file name, URL, date). Sources are listed in `../docs/DATA.md`.

- `fetch_eaglei.py` — EAGLE-I county outages (ORNL, DOI 10.13139/OLCF/2500278)
- `fetch_empower.py` — HHS emPOWER ZIP counts
- `fetch_storms.py` — NOAA HURDAT2 Atlantic tracks
