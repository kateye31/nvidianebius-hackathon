# Simulation (Nebius Serverless Job)

Everything here is **simulated** and labeled so in outputs and the UI.
Inputs come from real public data (see `docs/DATA.md`).

```bash
python sim/outage_sim.py --homes 2000 --med-share X --elderly-share Y
docker build -f sim/Dockerfile -t nightlight-sim .   # then run as a Serverless Job
```
