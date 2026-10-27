"""NWS heat index (Rothfusz regression) and tiers."""

def c_to_f(c: float) -> float: return c * 9 / 5 + 32
def f_to_c(f: float) -> float: return (f - 32) * 5 / 9


def heat_index_f(t_f: float, rh: float) -> float:
    simple = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + rh * 0.094)
    if (simple + t_f) / 2 < 80:
        return simple
    hi = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh - 0.22475541 * t_f * rh
          - 6.83783e-3 * t_f**2 - 5.481717e-2 * rh**2 + 1.22874e-3 * t_f**2 * rh
          + 8.5282e-4 * t_f * rh**2 - 1.99e-6 * t_f**2 * rh**2)
    if rh < 13 and 80 <= t_f <= 112:
        hi -= ((13 - rh) / 4) * ((17 - abs(t_f - 95)) / 17) ** 0.5
    elif rh > 85 and 80 <= t_f <= 87:
        hi += ((rh - 85) / 10) * ((87 - t_f) / 5)
    return hi


DANGER_F = 103.0

def tier(hi_f: float) -> int:
    """0 ok, 1 caution, 2 extreme caution, 3 danger, 4 extreme danger (NWS)."""
    if hi_f >= 125: return 4
    if hi_f >= 103: return 3
    if hi_f >= 90: return 2
    if hi_f >= 80: return 1
    return 0
