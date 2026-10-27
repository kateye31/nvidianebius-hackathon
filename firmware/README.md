# Firmware (ESP32)

1. Copy `nightlight_esp32/config.example.h` to `config.h` and fill in.
2. Arduino IDE: board "ESP32 Dev Module"; install *DHT sensor library* (Adafruit).
3. Flash, open Serial Monitor at 115200. Each packet prints as `{"p":"..."}`.

Wiring (confirm before powering):

| Part | ESP32 pin |
|---|---|
| DHT11 data | 4 |
| HC-SR501 PIR out | 27 |
| Grid sense (5 V USB charger -> 10k/20k divider) | 34 |
| SOS button (to GND) | 25 |
| Relay ch1 (AC, shed) | 26 |
| Relay ch2 (medical, keep) | 33 |
| Buzzer | 32 |
| OLED SDA/SCL | 21/22 |

Never connect anything to mains.
