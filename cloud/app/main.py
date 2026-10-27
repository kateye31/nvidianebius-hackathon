"""Nightlight API. Run: uvicorn app.main:app --reload"""
from __future__ import annotations
import base64, json, os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from . import db, packet  # noqa: E402
from .forecast import hours_to_unsafe  # noqa: E402
from .heat import c_to_f  # noqa: E402
from .scorer import score  # noqa: E402

app = FastAPI(title="Nightlight")
INGEST_KEY = os.environ.get("INGEST_KEY", "change-me")

# Real unit locations are set at install time. TODO(arwa): jittered demo coords.
UNIT_LOCATIONS: dict[int, tuple[float, float]] = {1: (26.62, -82.13)}


class Ingest(BaseModel):
    p: str                      # base64 of the 24-byte packet
    lat: float | None = None
    lon: float | None = None
    synthetic: bool = False     # sim job sets True


@app.get("/healthz")
def health(): return {"ok": True}


@app.post("/v1/ingest")
def ingest(body: Ingest, x_unit_key: str = Header(default="")):
    if x_unit_key != INGEST_KEY:
        raise HTTPException(401, "bad unit key")
    try:
        pk = packet.decode(base64.b64decode(body.p))
    except ValueError as e:
        raise HTTPException(400, str(e))
    lat, lon = (body.lat, body.lon) if body.lat is not None else UNIT_LOCATIONS.get(pk.unit_id, (0.0, 0.0))
    new = db.insert_reading(pk.to_dict(), lat, lon, body.synthetic)
    return {"stored": new, "unit_id": pk.unit_id}


def _home_view(row) -> dict:
    d = json.loads(row["data"])
    hist = [(r["received"], c_to_f(json.loads(r["data"])["heat_index_c"]))
            for r in db.history(d["unit_id"])]
    h = {**d, "lat": row["lat"], "lon": row["lon"], "synthetic": bool(row["synthetic"]),
         "heat_index_f": round(c_to_f(d["heat_index_c"]), 1),
         "hours_to_unsafe": hours_to_unsafe(hist)}
    return {**h, **score(h)}


@app.get("/v1/homes")
def homes():
    out = [_home_view(r) for r in db.latest_all()]
    return sorted(out, key=lambda h: h["risk"], reverse=True)


class CheckIn(BaseModel):
    unit_id: int
    text: str


@app.post("/v1/checkin")
async def checkin(body: CheckIn):
    from .agents.checkin_parser import parse
    parsed = await parse(body.text)
    with db.conn() as c:
        c.execute("INSERT INTO checkins VALUES (?, strftime('%s','now'), ?, ?)",
                  (body.unit_id, body.text, json.dumps(parsed)))
    return parsed


@app.get("/v1/brief")
async def brief(zip_code: str = "33956"):
    from .agents.crew_brief import write
    from .tools.tavily import live_context
    ranked = homes()
    ctx = await live_context(zip_code)
    return {"brief": await write(ranked, ctx), "context": ctx, "n_homes": len(ranked)}


DASH = Path(os.environ.get("DASHBOARD_DIR", Path(__file__).resolve().parents[2] / "dashboard"))
if DASH.exists():
    app.mount("/", StaticFiles(directory=DASH, html=True), name="dashboard")
