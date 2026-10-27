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
