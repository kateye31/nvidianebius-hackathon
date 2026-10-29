// Copy to config.h (gitignored) and fill in.
#pragma once
#define WIFI_SSID     "phone-hotspot-name"   // iPhone: turn on Maximize Compatibility (2.4 GHz)
#define WIFI_PASS     "hotspot-password"
// First test: a webhook.site URL (packets show up there). Then the real API:
//   https://YOUR-ENDPOINT/v1/ingest   or   http://LAPTOP_IP:8000/v1/ingest (laptop on same hotspot)
#define API_URL       "https://YOUR-ENDPOINT/v1/ingest"
#define INGEST_KEY    "change-me"            // must equal INGEST_KEY in the server's .env
#define UNIT_ID       1
#define OCCUPANTS     2
#define MEDICAL_LOAD  true     // a medical device depends on power in this home (flag only)

#define DEMO_SPEEDUP  900.0f   // demo clock: 1 real s = 15 simulated min. 1.0f = real time
#define MOTION_CM     8.0f     // raise to 12 if the ultrasonic reading jumps around
#define HAS_RELAY     0        // 1 only if you wired the optional 2-ch relay (GPIO25/33)
