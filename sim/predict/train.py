"""County outage forecaster. TODO(mate), Thursday.

Train: EAGLE-I 15-min county customers-out for Florida storms
       (Michael 2018, Irma 2017, Ian 2022, Idalia 2023, Helene 2024)
Test:  Milton 2024 (held out entirely).
Features per county x hour: distance to storm center, max sustained wind
(HURDAT2), forward speed, hours since landfall, customers served,
coastal flag, ACS share 65+.
Target: peak % customers out and hours to 50% restored.
Model: gradient boosting (sklearn HistGradientBoostingRegressor) — small, fast.
Report: MAE on Milton; plot predicted vs actual; feed predicted outage
duration into outage_sim.py as hours_per_feeder per county.
"""
