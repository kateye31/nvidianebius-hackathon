// Nightlight ESP32 — sensors -> 24-byte packet -> HTTPS POST via phone hotspot.
// Libraries: "DHT sensor library" (Adafruit, + Adafruit Unified Sensor). Nothing else.
// SAFETY: grid sense is a cut USB cable from a 5 V phone charger through a 1:2
// divider into GPIO26. Never mains. HC-SR04 echo (5 V) also goes through a divider.
//
// DEMO CLOCK: minutes dark, minutes since motion and uptime run DEMO_SPEEDUP times
// faster than real time (900x: 1 real s = 15 simulated min). Say so in the video.
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>
#include "mbedtls/base64.h"
#include "packet.h"
#include "config.h"

#ifndef DEMO_SPEEDUP
#define DEMO_SPEEDUP 900.0f    // 1.0f = real time
#endif
#ifndef MOTION_CM
#define MOTION_CM 8.0f         // distance jump that counts as "someone moved"; 12 if jumpy
#endif
#ifndef HAS_RELAY
#define HAS_RELAY 0            // optional 2-ch relay; not in the beginner kit
#endif

// ---- pins (matches the beginner build guide, section 4) ----
constexpr int PIN_DHT = 4;      // DHT11 data
constexpr int PIN_TRIG = 5;     // HC-SR04 trig
constexpr int PIN_ECHO = 18;    // HC-SR04 echo, through divider
constexpr int PIN_GRID = 26;    // charger 5 V through divider; or jumper from 3V3
constexpr int PIN_SOS = 27;     // button to GND, internal pull-up
constexpr int PIN_LED = 2;      // onboard LED
constexpr int PIN_RELAY_AC = 25;   // only if HAS_RELAY: AC / big load (shed first)
constexpr int PIN_RELAY_MED = 33;  // only if HAS_RELAY: medical load (keep on)
constexpr bool RELAY_ACTIVE_LOW = true;

constexpr uint32_t SEND_EVERY_MS = 5000;   // plus immediately on grid/SOS change
constexpr uint32_t SOS_HOLD_MS = 60000;    // SOS flag stays up for 60 real seconds
constexpr uint32_t DHT_EVERY_MS = 2000;    // DHT11 can't be read faster than ~1 Hz
constexpr uint8_t BATTERY_UNKNOWN = 255;   // a plain power bank reports nothing

DHT dht(PIN_DHT, DHT11);

uint16_t seq = 0;
uint32_t lastMotionMs = 0, gridLostMs = 0, lastSendMs = 0, lastDhtMs = 0, sosUntilMs = 0;
bool gridWas = true, sosWas = false, haveDht = false;
float lastCm = -1, tF = 75, rh = 50;
volatile bool sosPressed = false;

void IRAM_ATTR onSos() { sosPressed = true; }   // never miss a press during a POST

void relay(int pin, bool on) { digitalWrite(pin, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }

// Demo-clock helpers: real milliseconds -> simulated minutes / seconds.
uint16_t simMinutes(uint32_t ms) {
  float m = ms / 60000.0f * DEMO_SPEEDUP;
  return m > 65535 ? 65535 : (uint16_t)m;
}
uint32_t simSeconds(uint32_t ms) { return (uint32_t)(ms / 1000.0 * DEMO_SPEEDUP); }

// NWS heat index (Rothfusz), Fahrenheit in and out. Same formula as cloud/app/heat.py.
float heatIndexF(float T, float RH) {
  float hi = 0.5f * (T + 61.0f + (T - 68.0f) * 1.2f + RH * 0.094f);
  if ((hi + T) / 2 < 80) return hi;
  return -42.379f + 2.04901523f * T + 10.14333127f * RH - 0.22475541f * T * RH
         - 0.00683783f * T * T - 0.05481717f * RH * RH + 0.00122874f * T * T * RH
         + 0.00085282f * T * RH * RH - 0.00000199f * T * T * RH * RH;
}

// Contract tiers (docs/PACKET.md): 0 ok, 1 caution, 2 extreme caution, 3 danger, 4 extreme danger.
uint8_t tierF(float f) { return f >= 125 ? 4 : f >= 103 ? 3 : f >= 90 ? 2 : f >= 80 ? 1 : 0; }

float fToC(float f) { return (f - 32) * 5 / 9; }

float readCm() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long us = pulseIn(PIN_ECHO, HIGH, 30000);
  return us == 0 ? -1 : us * 0.0343f / 2;   // -1 = no echo
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_GRID, INPUT_PULLDOWN);
  pinMode(PIN_SOS, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_SOS), onSos, FALLING);
#if HAS_RELAY
  pinMode(PIN_RELAY_AC, OUTPUT);
  pinMode(PIN_RELAY_MED, OUTPUT);
  relay(PIN_RELAY_AC, true);
  relay(PIN_RELAY_MED, true);
#endif
  dht.begin();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);   // phone hotspot, 2.4 GHz
  uint32_t t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 10000) delay(250);
  Serial.printf("wifi %s\n", WiFi.status() == WL_CONNECTED ? "connected" : "not yet (will retry)");
  gridWas = digitalRead(PIN_GRID) == HIGH;
  if (!gridWas) gridLostMs = millis();
  lastMotionMs = millis();
}

// Offline queue: when the hotspot drops, packets wait here (FIFO, static memory)
// and go out in order once it is back, so the cloud sees the whole outage.
constexpr int QUEUE_N = 48;                 // 4 min of 5 s packets; oldest dropped when full
constexpr int FLUSH_PER_LOOP = 8;           // keep the loop (LED, SOS, sensors) responsive
NightlightPacket queueBuf[QUEUE_N];
int qHead = 0, qLen = 0;

void enqueue(const NightlightPacket& p) {
  if (qLen == QUEUE_N) { qHead = (qHead + 1) % QUEUE_N; qLen--; Serial.println("queue full, dropped oldest"); }
  queueBuf[(qHead + qLen) % QUEUE_N] = p;
  qLen++;
}

// Returns the HTTP code, or a negative number if nothing was sent.
int postOne(const NightlightPacket& p) {
  char b64[48]; size_t olen = 0;
  mbedtls_base64_encode((unsigned char*)b64, sizeof(b64), &olen, (const uint8_t*)&p, sizeof(p));
  char body[80];
  snprintf(body, sizeof(body), "{\"p\":\"%s\"}", b64);
  WiFiClientSecure tls; tls.setInsecure();    // hackathon demo; TODO(arwa): pin endpoint cert
  HTTPClient http;
  http.setTimeout(5000);
  bool ok = strncmp(API_URL, "https", 5) == 0 ? http.begin(tls, API_URL) : http.begin(API_URL);
  if (!ok) { Serial.println("bad API_URL"); return -100; }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Unit-Key", INGEST_KEY);
  int code = http.POST((uint8_t*)body, strlen(body));
  http.end();
  return code;
}

void sendPacket(const NightlightPacket& p) {
  enqueue(p);
  if (WiFi.status() != WL_CONNECTED) { Serial.printf("no wifi, queued (%d waiting)\n", qLen); return; }
  for (int i = 0; i < FLUSH_PER_LOOP && qLen > 0; i++) {
    int code = postOne(queueBuf[qHead]);
    Serial.printf("POST seq %u -> %d\n", queueBuf[qHead].seq, code);
    if (code < 200 || code >= 500) break;   // network/server trouble: keep it, retry next loop
    // 2xx stored; 4xx will never succeed (bad key/packet), so drop rather than block the queue
    qHead = (qHead + 1) % QUEUE_N; qLen--;
  }
  if (qLen > 0) Serial.printf("%d packet(s) still queued\n", qLen);
}

void loop() {
  uint32_t now = millis();

  // Motion: the ultrasonic sensor faces a doorway; a distance jump means someone moved.
  float cm = readCm();
  if (cm > 0 && lastCm > 0 && fabsf(cm - lastCm) > MOTION_CM) lastMotionMs = now;
  if (cm > 0) lastCm = cm;

  if (sosPressed || digitalRead(PIN_SOS) == LOW) { sosPressed = false; sosUntilMs = now + SOS_HOLD_MS; }
  bool sos = (int32_t)(sosUntilMs - now) > 0;

  bool grid = digitalRead(PIN_GRID) == HIGH;
  if (gridWas && !grid) gridLostMs = now;   // grid just died

#if HAS_RELAY
  relay(PIN_RELAY_AC, grid);    // on backup power: shed the AC, keep the medical load
  relay(PIN_RELAY_MED, true);
#endif

  if (now - lastDhtMs >= DHT_EVERY_MS) {
    lastDhtMs = now;
    float t = dht.readTemperature(true), h = dht.readHumidity();   // true = Fahrenheit
    if (!isnan(t) && !isnan(h)) { tF = t; rh = h; haveDht = true; }
    else Serial.println("DHT read failed (keeping last value)");
  }
  float hiF = heatIndexF(tF, rh);

  // LED: off = grid ok, solid = on backup power, fast blink = SOS.
  digitalWrite(PIN_LED, sos ? (now / 150) % 2 : !grid);

  bool changed = grid != gridWas || sos != sosWas;
  gridWas = grid; sosWas = sos;
  if (!changed && now - lastSendMs < SEND_EVERY_MS) { delay(200); return; }
  lastSendMs = now;

  NightlightPacket p{};
  p.version = 1;
  p.unit_id = UNIT_ID;
  p.seq = seq++;
  p.flags = (grid ? F_GRID : 0) | (sos ? F_SOS : 0) | (MEDICAL_LOAD ? F_MED : 0)
            | ((HAS_RELAY && !grid) ? F_SHED : 0);   // F_GEN: stretch (photoresistor flicker)
  p.battery_pct = BATTERY_UNKNOWN;
  p.temp_c_x10 = (int16_t)lroundf(fToC(tF) * 10);
  p.humidity_pct = (uint8_t)lroundf(rh);
  p.heat_index_c_x10 = (int16_t)lroundf(fToC(hiF) * 10);
  p.heat_tier = tierF(hiF);
  p.min_since_motion = simMinutes(now - lastMotionMs);
  p.min_dark = grid ? 0 : simMinutes(now - gridLostMs);
  p.occupants = OCCUPANTS;
  p.uptime_s = simSeconds(now);
  seal(p);

  // The real wire format, for judges: 24 bytes as hex.
  for (size_t i = 0; i < sizeof(p); i++) Serial.printf("%02X ", ((uint8_t*)&p)[i]);
  Serial.printf("(%u B) T=%.1fF RH=%.0f%% HI=%.1fF tier=%u grid=%d sos=%d dark=%umin still=%umin cm=%.0f%s\n",
                (unsigned)sizeof(p), tF, rh, hiF, p.heat_tier, grid, sos, p.min_dark,
                p.min_since_motion, cm, haveDht ? "" : " (no DHT yet)");
  sendPacket(p);
}
