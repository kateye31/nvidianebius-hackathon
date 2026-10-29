# Data sources (all real, public)

| Data | Use | Where |
|---|---|---|
| EAGLE-I outage records 2014–2024 (ORNL), 15-min county customers out | outage curves, prediction training | figshare 24237376 (DOI 10.6084/m9.figshare.24237376) |
| HHS emPOWER (ZIP-level Medicare electricity-dependent counts) | seeding medical-load share of synthetic homes | https://empowerprogram.hhs.gov/ (REST: `HHS_emPOWER_REST_Service_Public/FeatureServer/1`) |
| NOAA HURDAT2 / IBTrACS storm tracks | prediction features (Michael, Irma, Ian, Idalia, Helene; test Milton) | https://www.nhc.noaa.gov/data/hurdat/ |
| Census ACS (households, age 65+) | households and 65+ share per ZCTA (ACS 5-yr 2023, B11001, B11007) | https://api.census.gov/ (free key) |
| Census county gazetteer 2023 | county centroids and land area for the forecaster | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/ |
| NWS heat advisories, utility restoration updates | live context in crew brief | via Tavily at runtime |

Download into `data/raw/` with the scripts in `data/`. Raw files are
gitignored. Record the exact file name and download date in
`data/SOURCES.lock.md` so results are reproducible.
