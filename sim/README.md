# Simulation (Nebius Serverless Job)

Everything here is **simulated** and labeled so in outputs and the UI.
Inputs come from real public data (see `docs/DATA.md`): pass the emPOWER
electricity-dependent share as `--med-share` and the ACS 65+ share as
`--elderly-share`.

| Script | Question it answers | Output (`data/processed/`) |
|---|---|---|
| `outage_sim.py` | biggest-feeder-first vs Nightlight ordering: weighted person-hours above 103 °F | `sim_result.json` |
| `hubs.py` | where K resilience hubs / mobile batteries cover the most danger (`--judge`: 1 Nemotron Ultra call explains trade-offs) | `hubs.json` |
| `demand_response.py` | blue-sky heat peak: MW shaved by cycling AC in groups, never medical homes, capped comfort cost | `demand_response.json` |
| `predict/train.py` | county outage forecaster, tested on Milton (see `data/`) | `predict_milton.json` |

```bash
python sim/outage_sim.py --homes 2000 --med-share X --elderly-share Y
python sim/hubs.py --med-share X --elderly-share Y --k 5 --radius-km 2
python sim/demand_response.py --med-share X --elderly-share Y

# as a Nebius Serverless Job: build, push, run with the script as args
docker build -f sim/Dockerfile -t nightlight-sim .
docker run --rm -v "$PWD/data:/job/data" nightlight-sim sim/outage_sim.py --med-share X --elderly-share Y
```

## Milton forecaster: first result (real data, 2026-10-29)

Trained on 335 county×storm rows (Irma, Michael, Ian, Idalia, Helene), tested
on all 67 Florida counties for Milton, which the model never saw.

| Target | Model MAE | Baseline MAE (training mean) | Verdict |
|---|---|---|---|
| Peak % customers out | **10.8 pts** | 25.3 pts | useful: less than half the baseline error |
| Hours from peak to 50% restored | 15.1 h | **11.3 h** | not useful yet: worse than the baseline |

Known data issues: peaks are capped at 100% where EAGLE-I's modeled customer
count (MCC) is below the reported outages, and a few counties show very short
spikes (e.g. Volusia, 0.8 h to half restored), which distort the restoration
target. Use the peak-outage forecast; don't claim restoration-time skill.
