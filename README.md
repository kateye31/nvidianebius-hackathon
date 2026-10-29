# Nightlight

> Utilities can see the grid go dark. Nightlight sees who's still in the dark.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A $15 ESP32 box that keeps reporting from a Florida home after a hurricane
knocks the power out: grid on/off, indoor heat index, signs of life, an SOS
button, and a relay that sheds the AC to keep a medical device running on
backup power. The cloud ranks homes by danger with a deterministic scorer, and
NVIDIA Nemotron on Nebius Token Factory writes the crew's restoration brief.

**Track:** Physical AI · Nebius x NVIDIA Global AI Hackathon 2026

## What is real and what is simulated

| Real | Simulated (labeled in UI and data) |
|---|---|
| One ESP32 unit: DHT11 heat, HC-SR04 motion, grid sense, SOS, LED | the other homes on the map |
| Phone hotspot relay to the cloud | the island-wide outage scenario |
| Cloud API, scorer, Nemotron calls | |
| Public data: EAGLE-I, emPOWER, NOAA, Census | |

Honest limits:

- **One real unit.** Every other home on the map is synthetic and marked SIMULATED.
- **Accelerated clock.** The demo firmware runs hours dark / hours since
  motion 900× faster (1 real second = 15 simulated minutes), because nobody
  can wait 14 hours on camera. `DEMO_SPEEDUP 1.0` is real time.
- **Battery is not measured.** A plain power bank reports nothing, so the
  unit sends "unknown" (255) instead of a made-up percentage.
- **Motion is an ultrasonic distance change**, not a PIR (none in our kit).
- **The relay is optional** and not in the demo build; load shedding is
  designed (`HAS_RELAY`) but not filmed.
- If Token Factory is unreachable, the crew brief falls back to a template
  labeled "scorer only, Nemotron not called".

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Wire format:
[docs/PACKET.md](docs/PACKET.md).

```
ESP32 (DHT11, HC-SR04 motion, grid sense, SOS, LED) -> 24-byte packet
  -> phone hotspot -> HTTPS -> FastAPI on Nebius Serverless Endpoint
  -> SQLite -> risk scorer + hours-to-unsafe forecast
  -> Nemotron Nano (check-ins, per-home triage) / Super (crew brief) / Ultra (trade-offs)
  -> Leaflet console; dispatcher approves
Nebius Serverless Job: outage simulation + outage prediction
```

## Quick start

```bash
git clone https://github.com/kateye31/nvidianebius-hackathon.git
cd nvidianebius-hackathon
cp .env.example .env            # add NEBIUS_API_KEY and model IDs
cd cloud
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --host 0.0.0.0 --port 8000   # 0.0.0.0 so the ESP32 can reach it
# new terminal: one synthetic test unit, then a labeled simulated fleet
python tools_send_test_packet.py
python tools_send_test_packet.py --fleet 150 --med-share X --elderly-share Y  # emPOWER / ACS ratios
# open http://localhost:8000
```

API endpoints:

| Endpoint | What |
|---|---|
| `POST /v1/ingest` | the ESP32's 24-byte packet, base64 (`X-Unit-Key` header) |
| `POST /api/packet` | the same data as plain JSON, for curl/debugging (same header) |
| `GET /v1/homes` | homes ranked by the deterministic scorer |
| `GET /v1/brief` | crew brief: Nemotron Super, or a labeled scorer-only template |
| `POST /v1/checkin` | resident free text -> structured need (Nemotron Nano) |
| `GET /v1/triage?top=20` | one-line reason per top home (Nemotron Nano fan-out, semaphore 20) |
| `GET /v1/sim` | latest Serverless Job outputs from `data/processed/` (`SIM_DATA_DIR`), all simulated |
| `GET /v1/usage` | per-model Token Factory calls, tokens and average latency (for FEEDBACK.md) |

```bash
```

Hardware: see [firmware/README.md](firmware/README.md).
Simulation: see [sim/README.md](sim/README.md).

## How we used NVIDIA and Nebius

| What | Where |
|---|---|
| Nemotron Nano — check-in parsing, per-home triage fan-out | `cloud/app/agents/` |
| Nemotron Super — crew restoration brief grounded on scorer output | `cloud/app/agents/crew_brief.py` |
| Nemotron Ultra — a few hard trade-off calls | `sim/hubs.py` |
| Nebius Token Factory — all model calls (OpenAI-compatible API) | `cloud/app/agents/client.py` |
| Nebius Serverless Endpoint — hosts the API and console | `cloud/Dockerfile` |
| Nebius Serverless Job — outage simulation and prediction | `sim/Dockerfile` |

TODO(mate): add where Token Factory sped us up — read real numbers from `GET /v1/usage` after a demo run.

## Risk scoring

Deterministic and explainable; weights in `cloud/app/scorer.py`, formula in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The model explains the ranking;
it does not decide it.

## Safety and privacy

See [docs/SAFETY.md](docs/SAFETY.md). No mains wiring, no control of real grid
equipment, minimal personal data.

## Feedback on Nebius and NVIDIA tools

See [docs/FEEDBACK.md](docs/FEEDBACK.md).

## License

MIT — see [LICENSE](LICENSE).
