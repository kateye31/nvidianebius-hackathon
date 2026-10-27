"""Live context: NWS heat advisory + utility restoration ETA via Tavily."""
from __future__ import annotations
import os
import httpx


async def live_context(zip_code: str) -> str:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return ""
    q = f"National Weather Service heat advisory and power restoration estimate {zip_code} Florida today"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post("https://api.tavily.com/search",
                         json={"api_key": key, "query": q, "max_results": 5,
                               "include_answer": True})
        r.raise_for_status()
        data = r.json()
    srcs = "; ".join(x.get("url", "") for x in data.get("results", [])[:3])
    return f"{data.get('answer', '')} (sources: {srcs})"
