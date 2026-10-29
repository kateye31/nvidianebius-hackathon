# Data

Raw downloads go in `data/raw/` (gitignored). Processed tables go in
`data/processed/` (gitignored). Log every file you download in
`SOURCES.lock.md` (file name, URL, date). Sources are listed in `../docs/DATA.md`.

```bash
python data/fetch_storms.py    # NOAA HURDAT2 -> raw/hurdat2.txt (7 MB)
python data/fetch_eaglei.py    # EAGLE-I, Florida rows for 6 storms (streams ~5.5 GB, keeps a few MB)
python data/fetch_empower.py   # emPOWER FL ZIPs; + ACS ratios if CENSUS_API_KEY is set
python sim/predict/train.py    # trains on 5 storms, tests on Milton -> processed/predict_milton.json
```

| Script | Output |
|---|---|
| `fetch_storms.py` | `raw/hurdat2.txt`; `STORMS` list (Irma, Michael, Ian, Idalia, Helene; Milton held out) |
| `fetch_eaglei.py` | `raw/eaglei_fl_<storm>.csv`, `raw/eaglei_mcc.csv` (customers per county), `raw/fl_counties.csv` (centroids) |
| `fetch_empower.py` | `raw/empower_fl_zip.csv`; `processed/zip_ratios.csv` (med_share, elderly_share per ZIP) |

`zip_ratios.csv` feeds `--zip` in `sim/*.py` and `cloud/tools_send_test_packet.py`.
`med_share` = emPOWER electricity-dependent Medicare users / ACS households
(assumes about one user per household).
