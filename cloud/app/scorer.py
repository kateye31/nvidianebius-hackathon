"""Deterministic risk score. The LLM explains this; it never changes it."""
from __future__ import annotations

WEIGHTS = dict(heat=0.30, trend=0.20, dark=0.15, still=0.15,
               med=0.10, gen=0.05, occ=0.05)


def _c(x: float) -> float: return max(0.0, min(1.0, x))


def score(home: dict) -> dict:
    """home needs: heat_index_f, hours_to_unsafe (or None), min_dark,
    min_since_motion, medical_load, on_generator, occupants, sos."""
    h2u = home.get("hours_to_unsafe")
    parts = {
        "heat": _c((home["heat_index_f"] - 80) / 45),
        "trend": 0.0 if h2u is None else _c(1 - h2u / 12),
        "dark": _c(home["min_dark"] / 1440),
        "still": _c(home["min_since_motion"] / 720),
        "med": 1.0 if home["medical_load"] else 0.0,
        "gen": 1.0 if home["on_generator"] else 0.0,
        "occ": _c((home.get("occupants", 1) - 1) / 4),
    }
    risk = 100 * min(1.0, sum(WEIGHTS[k] * v for k, v in parts.items()))
    if home.get("sos"):
        risk = max(risk, 90.0)
    reasons = sorted(parts, key=lambda k: WEIGHTS[k] * parts[k], reverse=True)[:3]
    return {"risk": round(risk, 1), "parts": parts, "top_reasons": reasons}
