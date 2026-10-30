"""Nemotron Super: restoration brief grounded on scorer output."""
from __future__ import annotations
import json
from .client import chat, SUPER

SYSTEM = """You write a restoration brief for a utility crew dispatcher after a hurricane.
You are given ranked homes from a deterministic risk scorer. Do not re-rank.
Write plain text only: no markdown, no tables, no asterisks, no headings with #.
For each home write one line: "<rank>. Unit <id> (simulated if simulated) - risk <risk> - <reasons> - <one suggested action>".
Then one short paragraph on trade-offs. Then a section "Texts to residents:" with one plain sentence per home.
Quote numbers exactly as given. "no motion" means nobody was seen moving, which may be a person who cannot move.
The dispatcher makes the final decision."""


def _facts(h: dict, rank: int) -> dict:
    return {"rank": rank, "unit_id": h["unit_id"], "simulated": h["synthetic"], "risk": h["risk"],
            "grid": "on" if h["grid_present"] else "off", "reasons": h["reasons_plain"]}


async def write(ranked: list[dict], context: str = "", top_n: int = 5) -> str:
    payload = {"ranked_homes": [_facts(h, i) for i, h in enumerate(ranked[:top_n], 1)],
               "live_context": context}
    return (await chat(SUPER, SYSTEM, json.dumps(payload), max_tokens=900)).strip()


def template(ranked: list[dict], top_n: int = 8, reason: str = "") -> str:
    """No-LLM fallback built only from scorer fields, so the console still works
    without credits. Labeled so nobody mistakes it for a Nemotron brief."""
    lines = [f"TEMPLATE BRIEF (scorer only, Nemotron not called{': ' + reason if reason else ''})"]
    for i, h in enumerate(ranked[:top_n], 1):
        lines.append(
            f"{i}. Unit {h['unit_id']}{' (simulated)' if h.get('synthetic') else ''}: risk {h['risk']}"
            f" · grid {'on' if h.get('grid_present') else 'OFF'} · "
            + ", ".join(h.get("reasons_plain") or ["no risk factors yet"]))
    lines.append("The dispatcher makes the final decision.")
    return "\n".join(lines)
