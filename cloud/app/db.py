"""SQLite storage. One table of readings; current state = newest per unit."""
from __future__ import annotations
import json, os, sqlite3, time

DB_PATH = os.environ.get("DB_PATH", "nightlight.sqlite")


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS readings(
        unit_id INTEGER, seq INTEGER, uptime_s INTEGER, received REAL,
        lat REAL, lon REAL, synthetic INTEGER, data TEXT,
        UNIQUE(unit_id, seq, uptime_s))""")
    c.execute("""CREATE TABLE IF NOT EXISTS checkins(
        unit_id INTEGER, received REAL, text TEXT, parsed TEXT)""")
    # Install-time facts about a unit that are not in the 24-byte packet.
    c.execute("CREATE TABLE IF NOT EXISTS units(unit_id INTEGER PRIMARY KEY, zip TEXT)")
    return c


def set_zip(unit_id: int, zip_code: str) -> None:
    with conn() as c:
        c.execute("INSERT INTO units VALUES (?, ?) ON CONFLICT(unit_id) DO UPDATE SET zip=excluded.zip",
                  (unit_id, zip_code))


def zips() -> dict[int, str]:
    with conn() as c:
        return {r["unit_id"]: r["zip"] for r in c.execute("SELECT * FROM units")}


def insert_reading(d: dict, lat: float, lon: float, synthetic: bool) -> bool:
    with conn() as c:
        cur = c.execute("INSERT OR IGNORE INTO readings VALUES (?,?,?,?,?,?,?,?)",
                        (d["unit_id"], d["seq"], d["uptime_s"], time.time(),
                         lat, lon, int(synthetic), json.dumps(d)))
        return cur.rowcount == 1


def history(unit_id: int, limit: int = 30) -> list[sqlite3.Row]:
    with conn() as c:
        rows = c.execute("SELECT * FROM readings WHERE unit_id=? ORDER BY received DESC LIMIT ?",
                         (unit_id, limit)).fetchall()
    return rows[::-1]


def latest_all() -> list[sqlite3.Row]:
    with conn() as c:
        return c.execute("""SELECT r.* FROM readings r JOIN (
            SELECT unit_id, MAX(received) m FROM readings GROUP BY unit_id) x
            ON r.unit_id = x.unit_id AND r.received = x.m""").fetchall()
