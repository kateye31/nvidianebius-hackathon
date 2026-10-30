# AGENTS.md — instructions for AI coding agents

Read this before changing anything. It applies to every agent (Claude Code,
ChatGPT/Codex, Cursor, Copilot, Gemini). `CLAUDE.md` just points here.

## What this project is

**Nightlight** — "Utilities can see the grid go dark. Nightlight sees who's
still in the dark." A $15 ESP32 box in a Florida home that keeps reporting
after a hurricane outage: grid on/off, indoor heat index, signs of life (ultrasonic motion),
an SOS button, and a relay that sheds the AC to protect a medical load on
backup power. The cloud ranks homes by danger and Nemotron writes the crew's
restoration brief.

Hackathon: Nebius x NVIDIA Global AI Hackathon (Physical AI track, due
**Fri Oct 30 2026, 10:00 PDT**).

Read `docs/ARCHITECTURE.md` for the pipeline and `docs/PACKET.md` for the
wire format before touching firmware or ingest.

## Repo map

| Path | What | Owner |
|---|---|---|
| `firmware/` | ESP32 Arduino sketch, packet encoder | Arwa |
| `cloud/app/` | FastAPI ingest, scorer, forecast, Nemotron agents | teammate |
| `cloud/app/agents/` | Token Factory calls (Nano / Super / Ultra) | teammate |
| `sim/` | Nebius Serverless Job: outage sim, prediction, hubs, demand response | shared |
| `dashboard/` | Leaflet map console (plain HTML/JS, no build step) | teammate |
| `data/` | download scripts for real public data; raw files are gitignored | shared |
| `docs/` | architecture, packet contract, safety, demo, feedback | shared |

## Hard rules

1. **No fake data presented as real.** Anything simulated (fleet homes,
   island-wide outage) is labeled `synthetic: true` in data and shown as
   "SIMULATED" in the UI. Real sources are listed in `docs/DATA.md`.
2. **The packet contract is frozen.** `docs/PACKET.md`, `firmware/.../packet.h`
   and `cloud/app/packet.py` must match byte for byte. Changing one means
   changing all three and the test in `cloud/tests/test_packet.py`.
3. **Deterministic first, LLM second.** Ranking comes from `scorer.py`.
   Nemotron explains and drafts; it never decides priority on its own and its
   output must cite scorer fields.
4. **Human in the loop.** Nothing controls real grid equipment. The only
   actuator is the in-home relay on a low-voltage powerbank circuit.
5. **Secrets via env only** (`.env`, see `.env.example`). Never commit keys,
   never hardcode them, never log them.
6. **Minimal personal data.** Store a medical-load flag, not diagnoses. No
   names, no exact addresses in the repo; demo homes use jittered coords.
7. **Credits are small ($25).** Default to Nemotron Nano. Super for the crew
   brief. Ultra only for a few calls per run. Always set `max_tokens`. Use
   `asyncio.Semaphore` for fan-out.

## Commands

```bash
# cloud
cd cloud && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then fill in
uvicorn app.main:app --reload --port 8000   # dashboard at http://localhost:8000
pytest -q

# simulation (locally; same container runs as a Nebius Serverless Job)
python sim/outage_sim.py --homes 2000 --med-share <emPOWER> --elderly-share <ACS>

# fake a packet from the laptop (no hardware)
cd cloud && python tools_send_test_packet.py   # labeled synthetic
```

## Style

- Python 3.11, type hints, small pure functions, no frameworks beyond FastAPI.
- Firmware: Arduino C++ for ESP32, no dynamic allocation in the loop.
- Keep files short. Prefer editing an existing stub over adding a new module.
- Every TODO has an owner tag: `TODO(arwa)` or `TODO(mate)`.
- Commit messages: `area: what changed` (e.g. `firmware: add PIR debounce`).

## Before you say "done"

- `pytest -q` passes.
- Packet round-trip test passes if you touched packet code.
- Anything you simulated is labeled as simulated.
- README still describes how to run what you changed.
