"""Synthetic homes for a ZIP, seeded from REAL public ratios.
Every home is labeled synthetic=True. TODO(mate): load ratios from data/processed."""
from __future__ import annotations
import random


def seed(n_homes: int, med_share: float, elderly_share: float, n_feeders: int,
         center=(26.62, -82.13), rng: random.Random | None = None) -> list[dict]:
    """med_share: emPOWER electricity-dependent beneficiaries / households for the ZIP.
    elderly_share: ACS share of households with someone 65+."""
    rng = rng or random.Random(0)
    # feeder sizes are uneven in reality; a few large, many small
    weights = [rng.paretovariate(1.5) for _ in range(n_feeders)]
    homes = []
    for i in range(n_homes):
        f = rng.choices(range(n_feeders), weights)[0]
        elderly = rng.random() < elderly_share
        homes.append(dict(
            unit_id=100000 + i, feeder=f, synthetic=True,
            lat=center[0] + rng.gauss(0, 0.03), lon=center[1] + rng.gauss(0, 0.03),
            medical_load=rng.random() < med_share,
            occupants=rng.choice([1, 1, 2, 2, 3, 4]),
            elderly=elderly,
            # indoor heat-index rise after AC loss, F/hour (TODO: fit from our real DHT runs)
            hi_rise=rng.uniform(0.8, 2.2) * (1.15 if elderly else 1.0),
            hi_start=rng.uniform(78, 84),
        ))
    return homes
