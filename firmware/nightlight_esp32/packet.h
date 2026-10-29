// Packet contract v1 — must match docs/PACKET.md and cloud/app/packet.py
#pragma once
#include <stdint.h>
#include <string.h>

enum : uint8_t { F_GRID = 1, F_SOS = 2, F_GEN = 4, F_SHED = 8, F_MED = 16 };
// battery_pct 255 = unknown. min_since_motion, min_dark, uptime_s use the device
// clock, which runs DEMO_SPEEDUP times faster than real time in the demo build.

#pragma pack(push, 1)
struct NightlightPacket {
  uint8_t  version;          // 1
  uint16_t unit_id;
  uint16_t seq;
  uint8_t  flags;
  uint8_t  battery_pct;      // 0-100, 255 = unknown
  int16_t  temp_c_x10;
  uint8_t  humidity_pct;
  int16_t  heat_index_c_x10;
  uint8_t  heat_tier;
  uint16_t min_since_motion;
  uint16_t min_dark;
  uint8_t  occupants;
  uint32_t uptime_s;
  uint16_t crc16;            // CRC-16/CCITT-FALSE over the 22 bytes above
};
#pragma pack(pop)
static_assert(sizeof(NightlightPacket) == 24, "packet must be 24 bytes");

inline uint16_t crc16_ccitt(const uint8_t* d, size_t n) {
  uint16_t crc = 0xFFFF;
  while (n--) {
    crc ^= (uint16_t)(*d++) << 8;
    for (int i = 0; i < 8; i++) crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
  }
  return crc;
}

inline void seal(NightlightPacket& p) {
  p.crc16 = crc16_ccitt((const uint8_t*)&p, sizeof(p) - 2);  // ESP32 is little-endian
}
