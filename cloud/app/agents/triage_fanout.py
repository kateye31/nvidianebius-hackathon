"""Nemotron Nano fan-out: one short reason line per home, concurrently."""
from __future__ import annotations
import asyncio, json
from .client import chat, NANO

SYSTEM = "In at most 15 words, say why this home is at the given risk. Use only the JSON fields."
_limit = asyncio.Semaphore(20)


async def _one(home: dict) -> tuple[int, str]:
    async with _limit:
        try:
            return home["unit_id"], (await chat(NANO, SYSTEM, json.dumps(home), max_tokens=40)).strip()
        except Exception as e:  # keep the run going; scorer still ranks
            return home["unit_id"], f"(no explanation: {type(e).__name__})"


async def explain_all(homes: list[dict]) -> dict[int, str]:
    return dict(await asyncio.gather(*(_one(h) for h in homes)))
