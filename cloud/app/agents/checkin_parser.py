"""Nemotron Nano: messy resident text -> structured need."""
from __future__ import annotations
import json
from .client import chat, NANO

SYSTEM = """You turn a short message from a resident during a power outage into JSON.
Keys: need (one of: oxygen, medication_cold, cooling, mobility, water, other, none),
deadline_hours (number or null, how long until it becomes critical),
medical (true/false), summary (max 12 words). Use only facts in the message.
Return JSON only."""


async def parse(text: str) -> dict:
    out = await chat(NANO, SYSTEM, text, max_tokens=150, json_mode=True)
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"need": "other", "deadline_hours": None, "medical": False,
                "summary": text[:60], "parse_error": True}
