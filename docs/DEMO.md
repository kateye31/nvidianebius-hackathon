# Demo video plan

## Hardware minute (Physical AI track, one take, landscape)

Box, laptop (map) and phone all in frame. Phone on a stack of books. Record
the laptop screen separately and cut it in. Do 3 takes, keep the best.

| Time | Do | Say |
|---|---|---|
| 0:00–0:10 | Hold up the box, point at the sensors | "Utilities can see the grid go dark. Nightlight sees who is still in the dark." |
| 0:10–0:20 | Box on power bank, charger plugged in; map shows the real unit green | "One real unit. The other homes on this map are simulated." |
| 0:20–0:30 | Unplug the wall charger. LED goes solid; within 5 s the map shows grid OFF and hours dark counting | "The clock is accelerated 900 times for the demo." |
| 0:30–0:42 | Cup hands around the DHT11 | Heat index climbs, tier rises, dot goes orange |
| 0:42–0:50 | Stay still ("hours still" climbs), then press SOS. LED blinks fast, map row turns red with SOS | |
| 0:50–1:00 | Click "Crew brief": this home ranks first, and why | "Utilities restore by feeder size. We restore by who is in danger." |

Before filming: `python tools_send_test_packet.py --fleet 150 --med-share X --elderly-share Y`
to load the labeled simulated homes (X, Y from emPOWER/ACS, see `docs/DATA.md`).

## Full video (≤ 3 min)

1. 0:00–0:15 Problem: Florida outages, heat deaths after Ian/Milton, utilities see feeders not people.
2. 0:15–1:15 The hardware minute above.
3. 1:15–2:10 Console: ranked homes, Nemotron crew brief citing scorer fields,
   Tavily heat advisory, a check-in parsed by Nano.
4. 2:10–2:45 Serverless Job: biggest-feeder-first vs Nightlight ordering,
   person-hours in danger. Simulated parts labeled.
5. 2:45–3:00 How Nebius + NVIDIA were used; repo link.

## Fallbacks (decide at the checkpoint, don't loop)

- Motion flaky at 4 PM Thu: drop it; keep hours dark and SOS.
- No POST reaching the API at 6 PM Thu: film the Serial Monitor and
  webhook.site side by side. Still a real device sending real data.
- DHT11 dead: fake the heat input with a labeled test value in code and say so.
- No Token Factory credits: the console shows a labeled TEMPLATE brief built
  from the scorer only.

## Submission checklist

- [ ] Public repo, MIT license, README says what is real and what is simulated
- [ ] Wiring photo (`docs/wiring.jpg`) and the diagram in `docs/ARCHITECTURE.md`
- [ ] Video plays in a private browser window
- [ ] Devpost fields complete, track selected, teammate added
- [ ] Nemotron + Nebius usage in the description
- [ ] Submitted by 11:00 AM Friday; screenshot of the confirmation
