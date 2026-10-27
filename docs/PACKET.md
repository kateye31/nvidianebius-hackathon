# Packet contract v1 (frozen)

24 bytes, little-endian, no padding. Python format: `<BHHBBhBhBHHBIH`.
Must match `firmware/nightlight_esp32/packet.h` and `cloud/app/packet.py`.

| Off | Size | Field | Type | Notes |
|---|---|---|---|---|
| 0 | 1 | version | u8 | `1` |
| 1 | 2 | unit_id | u16 | |
| 3 | 2 | seq | u16 | wraps; reboot resets |
| 5 | 1 | flags | u8 | bit0 grid_present, bit1 sos, bit2 on_generator_suspected, bit3 ac_shed, bit4 medical_load_on |
| 6 | 1 | battery_pct | u8 | 0–100 |
| 7 | 2 | temp_c_x10 | i16 | 31.4 °C -> 314 |
| 9 | 1 | humidity_pct | u8 | |
| 10 | 2 | heat_index_c_x10 | i16 | computed on device |
| 12 | 1 | heat_tier | u8 | 0 ok, 1 caution, 2 extreme caution, 3 danger, 4 extreme danger |
| 13 | 2 | min_since_motion | u16 | saturates at 65535 |
| 15 | 2 | min_dark | u16 | minutes since grid lost, 0 if grid present |
| 17 | 1 | occupants | u8 | set at install |
| 18 | 4 | uptime_s | u32 | |
| 22 | 2 | crc16 | u16 | CRC-16/CCITT-FALSE over bytes 0–21 |

Transport: `POST /v1/ingest` with JSON `{"p": "<base64 of 24 bytes>"}` and
header `X-Unit-Key`. Server keeps only the newest `(unit_id, uptime_s)` as
current state; duplicates are `(unit_id, seq, uptime_s)` matches.
