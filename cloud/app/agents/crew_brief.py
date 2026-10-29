"""Nemotron Super: restoration brief grounded on scorer output."""
from __future__ import annotations
import json
from .client import chat, SUPER

SYSTEM = """You write a restoration brief for a utility crew dispatcher after a hurricane.
You are given ranked homes as JSON from a deterministic risk scorer. Do not re-rank.
For the top homes, give: rank, unit id, risk, the scorer's top_reasons in plain words,
hours_to_unsafe, and one suggested action. Then one paragraph on trade-offs.
Then a 1-sentence plain-language text message for each top home's resident.
Quote numbers exactly as given. Mark anything with synthetic=true as (simulated).
The dispatcher makes the final decision."""


async def write(ranked: list[dict], context: str = "", top_n: int = 8) -> str:
    payload = {"ranked_homes": ranked[:top_n], "live_context": context}
    return await chat(SUPER, SYSTEM, json.dumps(payload), max_tokens=900)


WHY = dict(heat="indoor heat index high", trend="heating toward danger", dark="long time without power",
           still="no movement detected", med="medical device depends on power",
           gen="generator suspected", occ="several occupants")


def template(ranked: list[dict], top_n: int = 8, reason: str = "") -> str:
    """No-LLM fallback built only from scorer fields, so the console still works
    without credits. Labeled so nobody mistakes it for a Nemotron brief."""
    lines = [f"TEMPLATE BRIEF (scorer only, Nemotron not called{': ' + reason if reason else ''})"]
    for i, h in enumerate(ranked[:top_n], 1):
        h2u = h.get("hours_to_unsafe")
        lines.append(
            f"{i}. Unit {h['unit_id']}{' (simulated)' if h.get('synthetic') else ''}: risk {h['risk']}"
            f"{' · SOS' if h.get('sos') else ''} · grid {'on' if h.get('grid_present') else 'OFF'}"
            f" · HI {h['heat_index_f']} F · "
            + ("already unsafe" if h2u == 0 else f"{h2u} h to unsafe" if h2u is not None else "no heat trend yet")
            + " · " + ", ".join(WHY[r] for r in h["top_reasons"]))
    lines.append("The dispatcher makes the final decision.")
    return "\n".join(lines)
