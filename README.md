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
| ESP32 unit, sensors, relay, phone relay | the other homes on the map |
| Cloud API, scorer, Nemotron calls | the island-wide outage scenario |
| Public data: EAGLE-I, emPOWER, NOAA, Census | |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Wire format:
[docs/PACKET.md](docs/PACKET.md).

```
ESP32 (DHT11, PIR, grid sense, SOS, relay) -> 24-byte packet
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
uvicorn app.main:app --port 8000
# new terminal: send a test packet (labeled synthetic)
python tools_send_test_packet.py
# open http://localhost:8000
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

TODO: add where Token Factory sped us up (latency, cost per run).

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
