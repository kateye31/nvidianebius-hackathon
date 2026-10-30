"""Nightlight API. Run: uvicorn app.main:app --reload"""
from __future__ import annotations
import base64, json, os, struct, time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from . import db, packet  # noqa: E402
from .forecast import hours_to_unsafe  # noqa: E402
from .heat import c_to_f, f_to_c  # noqa: E402
from .scorer import score  # noqa: E402

app = FastAPI(title="Nightlight")
INGEST_KEY = os.environ.get("INGEST_KEY", "change-me")

# Real unit locations are set at install time. TODO(arwa): jittered demo coords.
UNIT_LOCATIONS: dict[int, tuple[float, float]] = {1: (26.62, -82.13)}
# ZIP of the installed real units (coarse on purpose: no addresses). Also the
# crew brief's default area. TODO(arwa): set HOME_ZIP in .env to the box's ZIP.
HOME_ZIP = os.environ.get("HOME_ZIP", "33956")
ZIP = r"^\d{5}$"


class Ingest(BaseModel):
    p: str                      # base64 of the 24-byte packet
    lat: float | None = None
    lon: float | None = None
    zip: str | None = Field(None, pattern=ZIP)   # not in the packet; set at install / by the sim
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
    return _store(pk, body.lat, body.lon, body.synthetic, body.zip)


def _store(pk: packet.Packet, lat: float | None, lon: float | None, synthetic: bool,
           zip_code: str | None = None) -> dict:
    if lat is None or lon is None:
        lat, lon = UNIT_LOCATIONS.get(pk.unit_id, (0.0, 0.0))
    if zip_code:
        db.set_zip(pk.unit_id, zip_code)
    new = db.insert_reading(pk.to_dict(), lat, lon, synthetic)
    return {"stored": new, "unit_id": pk.unit_id}


class JsonPacket(BaseModel):
    """Plain-JSON fields from the beginner build guide (debug / compat path)."""
    unit_id: int
    grid_present: bool
    sos: bool = False
    battery_pct: int = packet.BATTERY_UNKNOWN
    temp_f: float
    humidity: int
    heat_index_f: float
    heat_tier: int
    hours_since_motion: float = 0.0
    hours_dark: float = 0.0
    medical_load: bool = False
    occupants: int = 1
    uptime_s: int | None = None
    lat: float | None = None
    lon: float | None = None
    zip: str | None = Field(None, pattern=ZIP)
    synthetic: bool = False


@app.post("/api/packet")
def api_packet(b: JsonPacket, x_unit_key: str = Header(default="")):
    """Same data as /v1/ingest, as JSON. Converted into the frozen packet so the
    rest of the pipeline sees one format."""
    if x_unit_key != INGEST_KEY:
        raise HTTPException(401, "bad unit key")
    flags = ((packet.F_GRID if b.grid_present else 0) | (packet.F_SOS if b.sos else 0)
             | (packet.F_MED if b.medical_load else 0))
    up = b.uptime_s if b.uptime_s is not None else int(time.time())
    pk = packet.Packet(1, b.unit_id, up & 0xFFFF, flags, b.battery_pct,
                       round(f_to_c(b.temp_f), 1), b.humidity, round(f_to_c(b.heat_index_f), 1),
                       b.heat_tier, min(round(b.hours_since_motion * 60), 65535),
                       0 if b.grid_present else min(round(b.hours_dark * 60), 65535),
                       b.occupants, up & 0xFFFFFFFF)
    try:
        pk = packet.decode(packet.encode(pk))   # range-checks every field
    except (ValueError, struct.error) as e:
        raise HTTPException(400, f"field out of range: {e}")
    return _store(pk, b.lat, b.lon, b.synthetic, b.zip)


def _forecast_series(unit_id: int) -> list[tuple[float, float]]:
    """(device-clock seconds, heat index F), newest run only. The device clock is
    uptime_s, which is accelerated in demo builds, so the forecast is in the same
    (simulated) hours as min_dark. A reboot resets uptime, so keep the trailing
    increasing run."""
    pts = [(json.loads(r["data"])["uptime_s"], c_to_f(json.loads(r["data"])["heat_index_c"]))
           for r in db.history(unit_id)]
    run: list[tuple[float, float]] = []
    for t, hi in pts:
        if run and t <= run[-1][0]:
            run = []
        run.append((t, hi))
    return run


def _home_view(row, zips: dict[int, str]) -> dict:
    d = json.loads(row["data"])
    zip_code = zips.get(d["unit_id"]) or (HOME_ZIP if d["unit_id"] in UNIT_LOCATIONS else None)
    h = {**d, "lat": row["lat"], "lon": row["lon"], "synthetic": bool(row["synthetic"]), "zip": zip_code,
         "heat_index_f": round(c_to_f(d["heat_index_c"]), 1),
         "hours_to_unsafe": hours_to_unsafe(_forecast_series(d["unit_id"])),
         "battery_known": d["battery_pct"] != packet.BATTERY_UNKNOWN,
         "last_seen_s": round(time.time() - row["received"])}
    return {**h, **score(h)}


@app.get("/v1/homes")
def homes():
    zips = db.zips()
    out = [_home_view(r, zips) for r in db.latest_all()]
    # Equal risk: real units first (a real SOS outranks a simulated one), then by unit id.
    return sorted(out, key=lambda h: (-h["risk"], h["synthetic"], h["unit_id"]))


class CheckIn(BaseModel):
    unit_id: int
    text: str


@app.get("/v1/history")
def history(unit_id: int, limit: int = 120):
    """Recent readings for one unit, oldest first, with the wire packet as hex (Device tab)."""
    names = packet.Packet.__dataclass_fields__.keys()
    out = []
    for r in db.history(unit_id, min(limit, 500)):
        d = json.loads(r["data"])
        raw = packet.encode(packet.Packet(**{k: d[k] for k in names}))
        out.append({**d, "received": r["received"], "synthetic": bool(r["synthetic"]),
                    "temp_f": round(c_to_f(d["temp_c"]), 1),
                    "heat_index_f": round(c_to_f(d["heat_index_c"]), 1), "hex": raw.hex(" ").upper()})
    return out


@app.post("/v1/checkin")
async def checkin(body: CheckIn):
    from .agents.checkin_parser import parse
    if not body.text.strip():   # an empty message makes Nano invent a need
        raise HTTPException(422, "check-in text is empty")
    try:
        parsed = await parse(body.text)
    except Exception as e:  # no key / credits: say so instead of guessing a need
        raise HTTPException(503, f"Nemotron unavailable ({type(e).__name__}); check-in not parsed")
    with db.conn() as c:
        c.execute("INSERT INTO checkins VALUES (?, strftime('%s','now'), ?, ?)",
                  (body.unit_id, body.text, json.dumps(parsed)))
    return parsed


@app.get("/v1/brief")
async def brief(zip_code: str = HOME_ZIP):
    from .agents.crew_brief import template, write
    from .tools.tavily import live_context
    ranked = homes()
    try:
        ctx = await live_context(zip_code)
    except Exception as e:  # live context is optional; never block the brief
        ctx = f"(live context unavailable: {type(e).__name__})"
    try:
        text, source = await write(ranked, ctx), "nemotron"
    except Exception as e:  # no key / no credits / timeout: scorer-only brief, labeled
        text, source = template(ranked, reason=type(e).__name__), "template"
    return {"brief": text, "source": source, "context": ctx, "n_homes": len(ranked)}


@app.get("/v1/triage")
async def triage(top: int = 20):
    """Nemotron Nano fan-out: one short reason per top-ranked home (semaphore 20).
    The ranking is the scorer's; Nano only words it."""
    from .agents.triage_fanout import explain_all
    ranked = homes()[:max(1, min(top, 50))]
    return {"why": await explain_all(ranked)}


@app.get("/v1/usage")
def usage():
    from .agents.client import usage_summary
    return usage_summary()


DATA_DIR = Path(os.environ.get("SIM_DATA_DIR", Path(__file__).resolve().parents[2] / "data" / "processed"))


@app.get("/v1/sim")
def sim():
    """Latest Serverless Job outputs, if present. Each file carries its own
    `simulated` flag (the Milton forecaster is real data; the rest is simulated)."""
    out: dict = {}
    for name in ("sim_result", "hubs", "demand_response", "predict_milton"):
        f = DATA_DIR / f"{name}.json"
        if f.exists():
            d = json.loads(f.read_text())
            d.pop("trials", None)
            out[name] = d
    return out


DASH = Path(os.environ.get("DASHBOARD_DIR", Path(__file__).resolve().parents[2] / "dashboard"))
if DASH.exists():
    app.mount("/", StaticFiles(directory=DASH, html=True), name="dashboard")
