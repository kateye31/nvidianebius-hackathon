"""Nemotron Nano fan-out: one short reason line per home, concurrently."""
from __future__ import annotations
import asyncio, json
from .client import chat, NANO

SYSTEM = ("You get one home's risk score from a deterministic scorer and the scorer's reasons. "
          "Write one plain sentence of at most 15 words saying why it has that score. "
          "Use only the given reasons and numbers, add no new facts, do not rate the risk yourself. "
          "'no motion' means nobody was seen moving (someone may be unable to move), never an empty house. "
          "Reply with the sentence only.")
_limit = asyncio.Semaphore(20)


def _facts(home: dict) -> dict:
    """Only what the sentence may cite. The full row invites the model to
    guess at raw fields like parts or min_dark."""
    return {"risk": home["risk"], "reasons": home["reasons_plain"],
            "grid": "on" if home["grid_present"] else "off"}


async def _one(home: dict) -> tuple[int, str]:
    async with _limit:
        try:
            out = await chat(NANO, SYSTEM, json.dumps(_facts(home)), max_tokens=40)
            return home["unit_id"], out.strip().strip('"')
        except Exception as e:  # keep the run going; scorer still ranks
            return home["unit_id"], f"(no explanation: {type(e).__name__})"


async def explain_all(homes: list[dict]) -> dict[int, str]:
    return dict(await asyncio.gather(*(_one(h) for h in homes)))
