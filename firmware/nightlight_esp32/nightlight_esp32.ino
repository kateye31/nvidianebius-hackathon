// Nightlight ESP32 — sensors -> 24-byte packet -> HTTPS POST via phone hotspot.
// Libraries: "DHT sensor library" (Adafruit), "Adafruit SSD1306", ArduinoJson not needed.
// SAFETY: grid sense uses a 5 V USB charger through a 10k/20k divider. Never mains.
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>
#include "mbedtls/base64.h"
#include "packet.h"
#include "config.h"

// ---- pins (TODO(arwa): confirm against your wiring) ----
constexpr int PIN_DHT = 4;
constexpr int PIN_PIR = 27;
constexpr int PIN_GRID = 34;       // input-only ADC pin, divider output
constexpr int PIN_SOS = 25;        // button to GND, INPUT_PULLUP
constexpr int PIN_RELAY_AC = 26;   // channel 1: AC / big load (shed first)
constexpr int PIN_RELAY_MED = 33;  // channel 2: medical load (keep on)
constexpr int PIN_BUZZ = 32;
constexpr bool RELAY_ACTIVE_LOW = true;

constexpr uint32_t SEND_EVERY_MS = 30000;   // demo cadence; field would be ~5 min
DHT dht(PIN_DHT, DHT11);

uint16_t seq = 0;
uint32_t lastMotionMs = 0, gridLostMs = 0, lastSendMs = 0;
bool gridWasPresent = true, sosLatched = false;

void relay(int pin, bool on) { digitalWrite(pin, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW); }

float heatIndexC(float tC, float rh) { return dht.computeHeatIndex(tC, rh, false); }

uint8_t tierFromC(float hiC) {
  float f = hiC * 9 / 5 + 32;
  return f >= 125 ? 4 : f >= 103 ? 3 : f >= 90 ? 2 : f >= 80 ? 1 : 0;
}

bool gridPresent() { return analogRead(PIN_GRID) > 2000; }  // ~1.6 V threshold

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_SOS, INPUT_PULLUP);
  pinMode(PIN_RELAY_AC, OUTPUT);
  pinMode(PIN_RELAY_MED, OUTPUT);
  pinMode(PIN_BUZZ, OUTPUT);
  relay(PIN_RELAY_AC, true);
  relay(PIN_RELAY_MED, true);
  dht.begin();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  lastMotionMs = millis();
}

void sendPacket(const NightlightPacket& p) {
  uint8_t b64[48]; size_t olen = 0;
  mbedtls_base64_encode(b64, sizeof(b64), &olen, (const uint8_t*)&p, sizeof(p));
  String body = String("{\"p\":\"") + String((char*)b64).substring(0, olen) + "\"}";
  Serial.println(body);                       // always visible over serial
  if (WiFi.status() != WL_CONNECTED) return;  // TODO(arwa): queue last N packets
  WiFiClientSecure tls; tls.setInsecure();    // TODO: pin endpoint cert
  HTTPClient http;
  String url = API_URL;
  bool ok = url.startsWith("https") ? http.begin(tls, url) : http.begin(url);
  if (!ok) return;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Unit-Key", INGEST_KEY);
  Serial.printf("POST -> %d\n", http.POST(body));
  http.end();
}

void loop() {
  uint32_t now = millis();
  if (digitalRead(PIN_PIR)) lastMotionMs = now;
  if (digitalRead(PIN_SOS) == LOW) { sosLatched = true; tone(PIN_BUZZ, 2000, 200); }

  bool grid = gridPresent();
  if (gridWasPresent && !grid) gridLostMs = now;
  gridWasPresent = grid;

  // Load shedding: on battery, drop the AC channel, keep the medical channel.
  relay(PIN_RELAY_AC, grid);
  relay(PIN_RELAY_MED, true);

  if (now - lastSendMs < SEND_EVERY_MS && !sosLatched) { delay(50); return; }
  lastSendMs = now;

  float t = dht.readTemperature(), h = dht.readHumidity();
  if (isnan(t) || isnan(h)) { Serial.println("DHT read failed"); return; }
  float hi = heatIndexC(t, h);

  NightlightPacket p{};
  p.version = 1;
  p.unit_id = UNIT_ID;
  p.seq = seq++;
  p.flags = (grid ? F_GRID : 0) | (sosLatched ? F_SOS : 0) | (!grid ? F_SHED : 0) |
            (MEDICAL_LOAD ? F_MED : 0);   // F_GEN: stretch (photoresistor flicker)
  p.battery_pct = 100;                     // TODO(arwa): read powerbank if possible
  p.temp_c_x10 = (int16_t)lroundf(t * 10);
  p.humidity_pct = (uint8_t)lroundf(h);
  p.heat_index_c_x10 = (int16_t)lroundf(hi * 10);
  p.heat_tier = tierFromC(hi);
  p.min_since_motion = (uint16_t)min<uint32_t>((now - lastMotionMs) / 60000, 65535);
  p.min_dark = grid ? 0 : (uint16_t)min<uint32_t>((now - gridLostMs) / 60000, 65535);
  p.occupants = OCCUPANTS;
  p.uptime_s = now / 1000;
  seal(p);
  sendPacket(p);
  sosLatched = false;
  // TODO(arwa): OLED — "GRID LOST", tier, and hours-to-unsafe from the API response.
}
