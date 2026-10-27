"""Nebius Token Factory client (OpenAI-compatible)."""
from __future__ import annotations
import os
from openai import AsyncOpenAI

BASE_URL = os.environ.get("TOKEN_FACTORY_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
NANO = os.environ.get("NEMOTRON_NANO_MODEL", "")
SUPER = os.environ.get("NEMOTRON_SUPER_MODEL", "nvidia/nemotron-3-super-120b-a12b")
ULTRA = os.environ.get("NEMOTRON_ULTRA_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")

_client: AsyncOpenAI | None = None


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"])
    return _client


async def chat(model: str, system: str, user: str, max_tokens: int = 400,
               json_mode: bool = False) -> str:
    if not model:
        raise RuntimeError("model id not set; copy it from Token Factory -> Models into .env")
    kw = {"response_format": {"type": "json_object"}} if json_mode else {}
    r = await client().chat.completions.create(
        model=model, max_tokens=max_tokens, temperature=0.2,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}], **kw)
    return r.choices[0].message.content or ""
