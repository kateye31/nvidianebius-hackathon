"""Deterministic risk score. The LLM explains this; it never changes it."""
from __future__ import annotations

WEIGHTS = dict(heat=0.30, trend=0.20, dark=0.15, still=0.15,
               med=0.10, gen=0.05, occ=0.05)


def _c(x: float) -> float: return max(0.0, min(1.0, x))


def score(home: dict) -> dict:
    """home needs: heat_index_f, hours_to_unsafe (or None), min_dark,
    min_since_motion, medical_load, on_generator, occupants, sos.
    grid_present (if given) zeroes the dark part: power is back."""
    h2u = home.get("hours_to_unsafe")
    parts = {
        "heat": _c((home["heat_index_f"] - 80) / 45),
        "trend": 0.0 if h2u is None else _c(1 - h2u / 12),
        "dark": 0.0 if home.get("grid_present") else _c(home["min_dark"] / 1440),
        "still": _c(home["min_since_motion"] / 720),
        "med": 1.0 if home["medical_load"] else 0.0,
        "gen": 1.0 if home["on_generator"] else 0.0,
        "occ": _c((home.get("occupants", 1) - 1) / 4),
    }
    risk = 100 * min(1.0, sum(WEIGHTS[k] * v for k, v in parts.items()))
    if home.get("sos"):
        risk = max(risk, 90.0)
    # Only parts that actually add risk; an SOS home can have none.
    reasons = [k for k in sorted(parts, key=lambda k: WEIGHTS[k] * parts[k], reverse=True) if parts[k] > 0][:3]
    return {"risk": round(risk, 1), "parts": parts, "top_reasons": reasons,
            "reasons_plain": plain_reasons(home, reasons)}


def plain_reasons(home: dict, reasons: list[str]) -> list[str]:
    """Scorer reasons as short phrases with their numbers, for the console,
    the brief and the Nano prompt. "still" means no motion seen, which may be a
    person who cannot move, never an empty house."""
    h2u = home.get("hours_to_unsafe")
    say = {
        "heat": lambda: f"heat index {home['heat_index_f']:.0f} °F",
        "trend": lambda: "already past 103 °F" if h2u == 0 else f"unsafe (103 °F) in {h2u} h",
        "dark": lambda: f"no power {home['min_dark'] / 60:.1f} h",
        "still": lambda: f"no motion {home['min_since_motion'] / 60:.1f} h",
        "med": lambda: "medical device on power",
        "gen": lambda: "running a generator",
        "occ": lambda: f"{home.get('occupants', 1)} people home",
    }
    return (["SOS pressed"] if home.get("sos") else []) + [say[k]() for k in reasons]
