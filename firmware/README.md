# Firmware (ESP32)

One real unit: DHT11 heat, HC-SR04 ultrasonic as the motion sensor, a 5 V
phone charger as the "grid", an SOS button, the onboard LED. It sends the
frozen 24-byte packet ([docs/PACKET.md](../docs/PACKET.md)) through your
phone's hotspot to the API.

## Setup (first 45 minutes)

1. Arduino IDE 2.x. Settings -> Additional boards manager URLs:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`,
   then Boards Manager -> install **esp32 by Espressif Systems**.
2. Plug in with a *data* cable. No new port? Install the CP210x or CH340
   driver, or swap the cable.
3. Tools -> Board -> **ESP32 Dev Module**; Tools -> Port -> the new port.
4. Library Manager: **DHT sensor library** (Adafruit; accept "install all").
5. Copy `nightlight_esp32/config.example.h` to `config.h` (gitignored), fill in
   the hotspot name/password, `API_URL` and `INGEST_KEY`.
6. Upload (hold **BOOT** if it hangs on "Connecting..."). Serial Monitor at
   **115200**.

Test each sensor alone before trusting the merged sketch; the beginner build
guide has the per-sensor test sketches.

## Wiring (unplug the board while wiring)

ESP32 pins take **3.3 V max**. The charger's 5 V and the HC-SR04 echo (5 V)
each go through a 1:2 divider (R1 = 1k, R2 = 2k, or 10k/20k): signal -> R1 ->
junction -> R2 -> GND, junction -> GPIO.

| From | To | Notes |
|---|---|---|
| DHT11 VCC / GND / DATA | 3V3 / GND / **GPIO4** | bare 4-pin DHT11: 10k DATA -> 3V3 |
| HC-SR04 VCC / GND | **VIN (5 V)** / GND | unreliable on 3V3 |
| HC-SR04 TRIG | **GPIO5** | |
| HC-SR04 ECHO | divider -> **GPIO18** | |
| SOS button | **GPIO27** and GND | internal pull-up |
| Cut USB cable red (5 V) from charger | divider -> **GPIO26** | the "grid" |
| Cut USB cable black (GND) | ESP32 GND | shared ground is required |
| LED | GPIO2 (onboard) | off = grid ok, solid = on backup, fast blink = SOS |
| Optional relay ch1 / ch2 | GPIO25 / GPIO33 | set `HAS_RELAY 1`; AC shed, medical kept |

Power the ESP32 from a **power bank**, never from the charger you unplug.
No resistors for the grid divider? Jumper 3V3 -> GPIO26 and pull it out on
camera; say it is a stand-in switch for the wall-power sensor.

Point the ultrasonic sensor at a wall or doorway 50–100 cm away. A jump of
more than `MOTION_CM` (8 cm) between readings counts as motion.

## What it does

- Sends a packet every 5 s, and immediately when the grid or SOS changes.
- Prints each packet as 24 hex bytes plus a readable line, then `POST -> 200`.
- **Offline queue:** if the hotspot drops, up to 48 packets (4 min) wait in
  RAM and are sent in order when it comes back, so the outage timeline has no
  gap. Older packets are dropped first if it stays down longer.
- SOS stays flagged for 60 s after a press (an interrupt catches presses
  during a POST).
- **Demo clock:** `DEMO_SPEEDUP 900` means 1 real second = 15 simulated
  minutes, so 14 "hours" dark pass in about 56 s. `min_dark`,
  `min_since_motion` and `uptime_s` use this clock. Set `1.0f` for real time.
- **Battery:** sent as `255` (unknown). A plain power bank reports nothing,
  and we don't fake a number.

## Testing without the real API

Set `API_URL` to a webhook.site URL: every packet shows up there as
`{"p": "<base64>"}`. Next, run the API on your laptop, join the laptop to the
same hotspot, and use `http://LAPTOP_IP:8000/v1/ingest`. iPhone hotspot: turn
on **Maximize Compatibility** (the ESP32 only does 2.4 GHz).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Garbled serial | 115200 baud |
| "DHT read failed" | re-seat DATA on GPIO4; 10k pull-up on a bare sensor |
| `cm=-1` always | HC-SR04 on VIN not 3V3; check TRIG 5 and the echo divider into 18 |
| Motion fires constantly | aim at a flat wall, fix the sensor, `MOTION_CM 12` |
| grid always 0 | charger black wire to ESP32 GND; junction to GPIO26 |
| grid always 1 | junction wired straight to 5 V: **unplug now** |
| "no wifi, queued" | hotspot on 2.4 GHz, keep the hotspot screen open |
| `POST -> -1` | phone has no data, or wrong URL |
| `POST -> 401` | `INGEST_KEY` differs from the server's `.env` |
| `POST -> 400` | wrong packet; reflash the sketch that matches `packet.h` |

Never connect anything to mains.
