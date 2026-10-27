# Data sources (all real, public)

| Data | Use | Where |
|---|---|---|
| EAGLE-I outage records 2014–2024 (ORNL), 15-min county customers out | outage curves, prediction training | DOI 10.13139/OLCF/2500278 |
| HHS emPOWER (ZIP-level Medicare electricity-dependent counts) | seeding medical-load share of synthetic homes | https://empowerprogram.hhs.gov/ |
| NOAA HURDAT2 / IBTrACS storm tracks | prediction features (Michael, Irma, Ian, Idalia, Helene; test Milton) | https://www.nhc.noaa.gov/data/hurdat/ |
| Census ACS (households, age 65+) | home counts per ZIP/tract | https://data.census.gov/ |
| NWS heat advisories, utility restoration updates | live context in crew brief | via Tavily at runtime |

Download into `data/raw/` with the scripts in `data/`. Raw files are
gitignored. Record the exact file name and download date in
`data/SOURCES.lock.md` so results are reproducible.
