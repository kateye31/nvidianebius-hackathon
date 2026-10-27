"""Hours until indoor heat index crosses NWS 'danger' (103 F)."""
from __future__ import annotations
from .heat import DANGER_F


def hours_to_unsafe(samples: list[tuple[float, float]], max_hours: float = 48.0) -> float | None:
    """samples: [(unix_seconds, heat_index_f)], oldest first.
    Returns 0 if already unsafe, None if not rising or too few points."""
    if not samples:
        return None
    if samples[-1][1] >= DANGER_F:
        return 0.0
    if len(samples) < 3:
        return None
    t0 = samples[0][0]
    xs = [(t - t0) / 3600 for t, _ in samples]
    ys = [y for _, y in samples]
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx  # F per hour
    if slope <= 0.05:
        return None
    hrs = (DANGER_F - ys[-1]) / slope
    return round(min(hrs, max_hours), 1)
