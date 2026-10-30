# Who does what (final stretch, times Eastern)

| When | Arwa (hardware) | Teammate (cloud) | Done when |
|---|---|---|---|
| Thu 10:45–12:00 | parts check, Arduino IDE, blink test | API up, credits claimed | LED blinks; API 200 on a test POST |
| Thu 12–2 PM | wiring, per-sensor tests | map shows one dot from stored packets | each sensor prints sane numbers |
| Thu 2–4 PM | merged sketch posting to webhook.site over hotspot | scorer check, simulated fleet loaded | packets every 5 s on webhook.site |
| Thu 4–6 PM | point sketch at real API | Nemotron check-in parser | unplug charger -> map changes |
| Thu 6–8 PM | power-bank run, full sequence 3× | crew brief (Super) on scorer output; sim chart | 3 clean runs in a row |
| Thu 8–10 PM | film the hardware minute (`docs/DEMO.md`) | README, Devpost fields, `docs/FEEDBACK.md` | raw video saved in two places |
| Fri 7:30–9 AM | re-shoot only if weak; upload | final cut, private-window click-through | everything opens logged out |
| Fri 9–10:45 AM | submit on Devpost, screenshot | check the submission page | **submitted by 11:00 AM** |

Checkpoints: motion flaky at 4 PM -> drop it. No POST by 6 PM -> film serial +
webhook.site. Stuck 45 min on anything -> photo of wiring + serial, ask.

Stretch (only if Thu is clean): relay shed (`HAS_RELAY`), photoresistor
flicker -> generator suspected, `sim/hubs.py`, `sim/demand_response.py`.
